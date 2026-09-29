# Labo M0 — Observer son propre réseau

**Objectif** : rien ne sera configuré ici. Ton unique mission est de **relever des valeurs
réelles** sur la machine `h1` (passerelle, ARP, préfixe réseau, noms, MTU) et de les écrire
dans des fichiers. À la fin, le bouton **Vérifier** compare chaque fichier à l'état *vivant*
du nœud : si la valeur relevée a bougé ou est fausse, le check échoue. C'est exactement
comme ça qu'on dépanne un réseau : on observe avant de toucher.

Ouvre le terminal de `h1` en **cliquant sur le nœud dans la topologie** (panneau de gauche).
Tu peux aussi utiliser l'**éditeur de config intégré** pour créer/modifier les fichiers
`/root/obs/*.txt` sans quitter le navigateur.

Le répertoire `/root/obs/` est déjà créé par la plateforme.

## Étape 1 — La passerelle par défaut (IPv4)

Affiche ta table de routage :
```bash
ip route show default
```
La ligne ressemble à `default via 10.198.8.1 dev eth0`. L'adresse après `via`,
c'est la **passerelle** : le routeur vers qui tu envoies tout paquet hors de ton réseau.
Écris-la (IP seule, sans masque) dans le fichier :
```bash
echo '10.198.8.x' > /root/obs/gw_ipv4.txt
```

## Étape 2 — L'adresse MAC de la passerelle (ARP)

Pour parler à la passerelle sur le réseau local, ta machine a besoin de son **adresse
physique (MAC, couche 2)**. Réponds d'abord un ping pour peupler le cache ARP, puis
consulte-le :
```bash
ping -c1 -W1 $(cat /root/obs/gw_ipv4.txt)
arp -a
ip -o neigh get $(cat /root/obs/gw_ipv4.txt) dev eth0
```
Repère le champ `lladdr`. Écris la MAC (minuscules, séparées par `:`) dans le fichier :
```bash
echo 'aa:bb:cc:dd:ee:ff' > /root/obs/gw_mac.txt
```

## Étape 3 — Le préfixe de ton réseau de management

Regarde ton adresse et ton masque :
```bash
ip -4 addr show dev eth0
```
Avec l'adresse (ex. `10.198.8.2`) et le masque `/24`, **calcule l'adresse réseau**
(la base du préfixe). Tu peux confirmer avec la route de lien local :
```bash
ip -4 route show scope link dev eth0
```
Écris le préfixe au format `adresse/masque` (ex. `10.198.8.0/24`) :
```bash
echo '10.198.8.0/24' > /root/obs/mgmt_prefix.txt
```

## Étape 4 — Un nom interne inventé : la résolution de noms

La plateforme a inventé un nom d'hôte interne, `atelier.m0.internal`, enregistré sur ta
machine. Résous-le et note l'adresse obtenue :
```bash
getent hosts atelier.m0.internal
```
Écris l'adresse résolue dans le fichier :
```bash
echo '10.198.8.x' > /root/obs/dns_atelier.txt
```
Puis compare : quelle était ton adresse IPv4 à l'étape 3 ? Que t'apprend le fichier
`/etc/hosts` sur l'ordre de résolution des noms ?

## Étape 5 — Ton résolveur DNS

Qui interroges-tu quand un nom n'est pas dans `/etc/hosts` ? Regarde la configuration :
```bash
cat /etc/resolv.conf
```
Écris l'adresse du `nameserver` (le résolveur que la plateforme te fournit) dans le fichier :
```bash
echo '127.0.0.11' > /root/obs/resolver.txt
```

## Étape 6 — Le MTU de ton interface

Le MTU, c'est la taille maximale (en octets) que ta carte peut mettre dans une trame.
Deux façons de le relever :
```bash
ip link show dev eth0
cat /sys/class/net/eth0/mtu
```
Écris la valeur (nombre seul, sans unité) :
```bash
echo '1500' > /root/obs/mtu.txt
```

## Étape 7 — Vérifie

```bash
ls -l /root/obs/
cat /root/obs/*.txt
```
Quand les six fichiers existent et contiennent les valeurs relevées, clique sur
**Vérifier** dans le frontend : chaque bon relevé rapporte des points (total 10).
Astuce : les checks relisent l'état *vivant* au moment de la vérification — si tu
recopie une valeur avec `$(...)` au lieu de la deviner, elle sera juste par construction.
