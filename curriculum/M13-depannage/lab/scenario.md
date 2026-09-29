# Labo M13 — Dépannage structuré : le service « accès au serveur » est mort

**Symptôme (ticket ouvert par l'utilisateur)** : depuis `h1`, plus moyen d'atteindre le
serveur `h2` (10.13.3.20). Certains paquets semblent disparaître sans message d'erreur.
Le réseau n'a pas été modifié « à la main » depuis la dernière livraison… ou alors
n'importe qui a pu le faire.

**Objectif** : rétablir le service en un minimum de temps, en suivant une méthode
(layer by layer) plutôt qu'en tâtonnant, et savoir justifier chaque panne trouvée.
Il y a **plusieurs pannes simultanées** sur le chemin : le service ne reviendra que
lorsqu'elles seront toutes corrigées.

Cliquez sur un nœud pour ouvrir son **terminal**. L'**Éditeur de configuration** permet
de sauvegarder votre compte-rendu (par ex. `/root/postmortem.md`). Cliquez sur
**Vérifier** pour les 4 checks (10 points) : ils testent l'état de chaque maillon et le
ping de bout en bout.

## Documentation du réseau (référence à retrouver)

| Nœud | Interface | Adresse | Rôle |
|---|---|---|---|
| h1 | eth1 | 10.13.1.10/24 | client, passerelle 10.13.1.1 |
| r1 | eth1 / eth2 | 10.13.1.1/24 / 10.13.2.1/24 | routeur, `ip_forward=1` |
| r2 | eth1 / eth2 | 10.13.2.2/24 / 10.13.3.1/24 | routeur, `ip_forward=1` |
| h2 | eth1 | 10.13.3.20/24 | serveur, passerelle par défaut 10.13.3.1 |

Routes statiques documentées : `r1` → `10.13.3.0/24 via 10.13.2.2` ; `r2` →
`10.13.1.0/24 via 10.13.2.1`. Aucun protocole de routage dynamique sur ce site.

## Méthode (à suivre dans cet ordre)

### Couche 1-2 — le support et l'interface

```bash
ip -br link                 # état administratif ET porteur, sur chaque nœud
ip -br addr                 # adresses configurées
```

Un lien `DOWN` côté administratif se répare avec `ip link set <if> up` ; un lien `UP`
sans `LOWER_UP` est un problème de câble/VLAN (ici : nœud voisin éteint, interface down).
Sur un conteneur, `ip -br link` compare en un coup d'œil les deux extrémités d'un segment.

### Couche 3 — adressage et préfixe

```bash
ip -4 addr show dev eth1    # vérifier le MASQUE, pas seulement l'adresse
ip neigh                    # la table ARP est-elle remplie ?
ping -c2 <passerelle>       # le premier test à faire : je ping mon voisin direct
```

Un masque trop restrictif (/25 au lieu de /24) ne casse pas le ping vers le voisin
direct (il reste dans le sous-réseau calculé) mais supprime la route vers tout le reste :
`ip route get <destination>` est sans ambiguïté sur ce point.

### Couche 3bis — routage intermédiaire

```bash
# sur le routeur soupçonné :
ip route show
ip route show type blackhole        # des routes d'interception, ça existe aussi
ip route get 10.13.3.20             # que dit la FIB, réellement ?
```

Une route `blackhole` fait disparaître le trafic **sans message d'erreur** : le paquet
est jeté localement, éventuellement avec une `ICMP unreachable` selon le type (`unreach`
vs `blackhole` : le premier parle à l'émetteur, le second non). C'est le pire défaut à
trouver « à l'instinct », et le plus évident avec `ip route get`.

### Couche 3ter — bout en bout, en découpant le chemin

```bash
# depuis h1, dans l'ordre :
ping -c2 10.13.1.1     # ma passerelle
ping -c2 10.13.2.2     # le deuxième routeur (prouve r1 qui relaie)
ping -c2 10.13.3.1     # l'interface côté serveur
ping -c2 10.13.3.20    # le serveur
tracepath 10.13.3.20   # où s'arrête le chemin ?
```

Le premier saut qui ne répond pas délimine la zone de panne : tout ce qui est avant est
validé, on ne perd plus de temps à le re-vérifier.

### Couche 4-7 — service

```bash
# sur h2 :
ss -tlnp                   # le service écoute-t-il, et sur quelle adresse ?
# depuis h1 :
curl -v http://10.13.3.20:80/   # (adapter le port au service testé)
```

Un ping qui passe ne prouve pas le service ; un service qui écoute sur `127.0.0.1` ne
répondra jamais à distance. Réciproquement, `tcpdump -ni eth1 port 80` sur le serveur
distingue « la requête n'arrive pas » de « la requête arrive et je ne réponds pas ».

## Réparer, puis revalider

Quand vous tenez une cause : notez-la, corrigez-la, **re-testez le maillon concerné**,
puis reprenez la liste des tests de bout en bout. Ne corrigez pas trois choses à la fois —
vous ne sauriez plus laquelle a réglé le problème.

```bash
# exemples de corrections (à adapter à ce que VOUS avez trouvé) :
ip link set eth1 up                                  # interface éteinte
ip addr flush dev eth1 && ip addr add 10.13.3.20/24 dev eth1   # masque erroné
ip route replace default via 10.13.3.1                # route par défaut perdue
ip route del blackhole 10.13.3.0/24                   # interception retirée
ip route add 10.13.3.0/24 via 10.13.2.2               # route manquante recréée
```

## Livrables

1. `ping -c4 10.13.3.20` depuis `h1` à 0 % de perte.
2. Les trois états intermédiaires conformes à la documentation (lien, adressage, routage).
3. Un post-mortem dans `/root/postmortem.md` (éditeur, nœud `h1`) : pour chaque panne —
   **symptôme observé / commande qui l'a révélée / cause / correction / mesure de
   prévention** (par ex. `nftables` pour interdire un `ip link set down` non autorisé,
   supervision SNMP des états d'interface — cf. M10, politique de changement — cf. M15/M16).

Cliquez **Vérifier** à la fin : le score est la somme des maillons conformes, 10 points.
