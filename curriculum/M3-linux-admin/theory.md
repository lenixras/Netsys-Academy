# M3 — Linux administrateur : utilisateurs, réseau, noyau, journaux

> Vague 1 · Prérequis : M2 · Travaux pratiques : labo `m3-admin` (nœud `admin1`, 30 min)

## 1. Comptes et groupes : la trilogie /etc

L'identité sur Linux, ce sont trois fichiers texte (et une base NSS pour les modes
avancés type LDAP) :

### `/etc/passwd` — un compte par ligne, 7 champs séparés par `:`

```
devops:x:1500:1500::/home/devops:/bin/bash
  │    │  │     │    │  │           │
  nom  x  UID   GID  commentaire    shell de connexion
           principal  (GECOS, vide)  (/usr/sbin/nologin = pas d'interactive)
```

Le champ `x` signifie « mot de passe delegué à `/etc/shadow` ». L'**UID 0** est root
(un seul) ; les comptes système occupent les petits UID (< 1000 sur Debian) ; les
humains commencent à 1000. Fixer un UID à la main (`useradd -u`) est utile pour
synchroniser des permissions NFS ou un annuaire.

### `/etc/shadow` — les hachages de mots de passe

Mode `640 root:shadow` : pas de lecture pour les utilisateurs. Chaque ligne :
`nom:hachage:date_dernier_changement:âge_mini:âge_maxi:alerte:inactif:expire`.
Le hachage moderne est `y` (yescrypt) ou `sha-512` ; `!` ou `*` = compte verrouillé.
Un compte **sans mot de passe** n'est pas joignable par `su`/ssh par mot de passe :
`passwd devops` pour en définir un.

### `/etc/group` — groupes et membres secondaires

```
staff:x:50:devops,alice
nom:motdepasse:GID:membres
```

Chaque utilisateur a **un groupe principal** (champ GID de passwd) et **zéro ou
plusieurs groupes secondaires** (liste dans group, ou base NSS). Les fichiers
héritent du groupe principal à la création ; `chgrp` ou le bit SGID sur un
répertoire changent cela.

### Les commandes

```bash
useradd -u 1500 -m -s /bin/bash devops   # -m crée /home/devops, -u impose l'UID
usermod -aG staff devops                 # -a indispensable : sans -a, -G ÉCRASE les autres groupes
groupadd -f staff                        # -f : ne pas échouer si le groupe existe
userdel -r devops                        # -r supprime aussi le home
id devops        # uid=1500(devops) gid=1500(devops) groupes=1500(devops),50(staff)
id -nG devops    # seulement les noms de groupes
getent passwd devops   # lit via NSS : voit aussi les comptes LDAP/SSSD
getent group staff
```

`su - devops` change d'identité (le `-` recharge l'environnement de la cible).
`sudo` exécute **une** commande avec les droits d'un autre (root par défaut), selon
`/etc/sudoers` (jamais édité à cru : `visudo`, qui vérifie la syntaxe). Le drop-in
`/etc/sudoers.d/` est la voie propre pour délégations et labs.

## 2. systemd : ce que dit le cours… (théorie)

Sur une installation Linux « normale », `systemd` est le processus 1 : il démarre les
services, les supervise et les relance, et centralise les journaux. Le vocabulaire :

```bash
systemctl status ssh        # état d'une « unité »
systemctl start|stop|restart|enable ssh   # enable = démarrage automatique au boot
journalctl -u ssh -f        # journaux de l'unité, en direct
loginctl, systemctl list-units --type=service --state=running
```

Une *unit* est un fichier `/etc/systemd/system/*.service` (ou `/usr/lib/systemd/system`)
décrivant `ExecStart=`, dépendances, redémarrage. `target` = groupe d'unités
(`multi-user.target` ≈ runlevel 3 classique).

### …et la réalité du conteneur

Nos nœuds sont des conteneurs : PID 1 = `sleep infinity`, **pas de systemd, pas de
journald, pas de syslogd**. Conséquences pratiques — et c'est justement une
compétence d'administrateur moderne :

- pas de `systemctl` : on lance le binaire directement, en arrière-plan
  (`nohup python3 -m http.server 8080 &`) ;
- pas de `journalctl` : la sortie d'un processus va là où on la **redirige**
  (`>> /var/log/deploy.log`), et `logger` (client syslog) n'a personne à qui parler ;
- l'état du système se lit dans `/proc`, `/sys`, `ip`, `ss` : tout est réel, seule
  l'orchestration manque.

## 3. iproute2 : le réseau en commandes

La suite historique (`ifconfig`, `route`, `netstat`) est remplacée par **iproute2**.

```bash
ip -br link        # interfaces, état courte ligne (DOWN/up, MTU, MAC)
ip link set eth1 up          # activer l'interface (sans IP, rien ne circule)
ip -br addr        # adresses de toutes les interfaces
ip addr add 10.198.11.50/24 dev eth1    # AJOUTE une adresse (plusieurs possibles par interface)
ip addr del 10.198.11.50/24 dev eth1    # la retirer
ip addr flush dev eth1
ip route          # table de routage ; ip route add default via 10.0.0.1
ip neigh          # table ARP (l'équivalent de l'ancien arp -a)
```

Contrairement à `ifconfig eth1 10.0.0.5` qui **remplaçait** les adresses existantes,
`ip addr add` empile : une interface peut porter plusieurs IPv4/IPv6 (utile pour les
VIP, l'aliasing, les tests). L'interface doit être `up` pour émettre.

`ss` (socket statistics) remplace `netstat` :

```bash
ss -tln    # sockets TCP en ÉCOUTE, adresses numériques (-a = toutes connexions)
ss -tlnp   # + le processus propriétaire (nécessite root)
ss -s      # résumé global
```

`0.0.0.0:8080` en écoute signifie que le port est joignable sur **toutes** les
interfaces (dont eth1 et eth0 de management) ; `127.0.0.1:8080` le limiterait au local.
Vérifier qu'un service écoute avant de tester le pare-feu (M11) est un réflexe de diagnostic.

## 4. Régler le noyau : sysctl et /proc

Beaucoup de paramètres du noyau sont exposés dans `/proc/sys/` — un fichier par
valeur, dans une arborescence qui reprend les noms pointés :

`net.ipv4.ip_forward` ↔ `/proc/sys/net/ipv4/ip_forward`

```bash
cat /proc/sys/net/ipv4/ip_forward     # 0 = ne route pas, 1 = routeur
sysctl -w net.ipv4.ip_forward=1       # application immédiate, NON persistante
sysctl net.ipv4.ip_forward            # lecture
sysctl -a | grep ipv4                 # explorer
```

Pour la persistance : fichiers `.conf` dans `/etc/sysctl.d/` (ex.
`/etc/sysctl.d/99-routeur.conf` avec la ligne `net.ipv4.ip_forward = 1`), lus au boot
par `systemd-sysctl` (ou `sysctl --system` à la main). Un conteneur peut porter ces
valeurs dans son propre espace de noms réseau ; certains paramètres restent
globaux (kernel.*).

Activer `ip_forward` fait d'une machine un **routeur** : c'est la base du M5
(inter-VLAN), du NAT (M11) et des labs FRR (M6).

## 5. Journaux : /var/log côté fichier, journalctl côté systemd

Sur une distribution avec systemd, `journalctl` lit le *journal* binaire de journald,
qui collecte stdout des services, syslog, audits, avec des filtres par unité, boot,
priorité, période (`-u`, `-b`, `-p err`, `--since`). En l'absence de journald,
place aux **fichiers texte** de `/var/log` :

| Fichier | Contenu usuel |
|---|---|
| `/var/log/syslog`, `messages` | collectés par rsyslog/syslog-ng |
| `/var/log/auth.log`, `secure` | connexions, sudo, PAM |
| `/var/log/kern.log` | messages du noyau |
| `/var/log/dpkg.log` | opérations de paquets |
| `/var/log/<app>/` | log applicatif propre |
| `/var/log/deploy.log` | le vôtre, dans ce TP |

Écrire dans un log applicatif sans démon syslog : la redirection.

```bash
echo "$(date '+%F %T') deploiement v1 OK" >> /var/log/deploy.log
logger "message"      # client syslog : utile AVEC un démon, muet sinon
tail -f /var/log/deploy.log ; grep -i error /var/log/deploy.log
```

Rotation (`logrotate`) : les fichiers tournent en `.1`, `.2.gz`… pour ne pas remplir
le disque — un classique des pannes « plus d'espace » (voir M10/M13).

## 6. Config réseau déclarative : netplan et friends (théorie)

Un serveur ne configure pas ses adresses à la main à chaque boot : il le déclare.

- **netplan** (Ubuntu ≥ 18.04) : YAML dans `/etc/netplan/*.yaml`, traduit en config
  `systemd-networkd` (serveurs) ou NetworkManager (desktops) :
  ```yaml
  network:
    version: 2
    ethernets:
      eth1:
        addresses: [10.198.11.50/24]
        routes: [{to: default, via: 10.198.11.1}]
        nameservers: {addresses: [10.198.11.2]}
  ```
  `netplan apply` après édition.
- **Debian** : `/etc/network/interfaces` + `ifup/ifdown`.
- **RHEL** : `nmcli` / fichiers `ifcfg-*`.

Dans un conteneur éphémère, `ip addr add` suffit (état non persistant) : le labo
M3 fonctionne ainsi, et c'est aussi exactement ce que font les outils d'automatisation
(Ansible module `ansible.builtin.ip`, scripts des labs réseau).

## 7. Checklist de l'admin débutant

1. Identité : `id`, `getent passwd <user>`, `getent group <grp>` avant d'accuser « permission denied ».
2. Interface : `ip -br a` — est-ce up ? a-t-elle la bonne adresse ?
3. Routage : `ip route` — une route par défaut ? la bonne passerelle ?
4. Service : `ss -tlnp` — le bon port, la bonne adresse de bind (127.0.0.1 vs 0.0.0.0) ?
5. Noyau : `sysctl`/`/proc/sys` — forwarding, pare-feu, limites.
6. Logs : `/var/log/*` ou `journalctl -u <svc>` — la cause est presque toujours écrite quelque part.

## 8. Mémo express

| Objectif | Commande |
|---|---|
| compte avec UID fixe | `useradd -u 1500 -m -s /bin/bash devops` |
| groupe secondaire sans rien casser | `usermod -aG staff devops` |
| lire un compte via NSS | `getent passwd devops` |
| ajouter une IP sans écraser | `ip addr add 10.198.11.50/24 dev eth1` |
| sockets TCP en écoute | `ss -tln` |
| activer le routeur | `sysctl -w net.ipv4.ip_forward=1` (persistant : `/etc/sysctl.d/`) |
| journaliser sans syslogd | `echo "..." >> /var/log/deploy.log` |
| service en sandbox | `nohup python3 -m http.server 8080 > /dev/null 2>&1 &` |

Validez par le quiz (≥ 70 %), puis le labo `m3-admin` : les six checks (user devops
1500, membre staff, IP secondaire, ip_forward=1, port 8080 en écoute, deploy.log non
vide) reproduisent exactement les commandes de ce cours.
