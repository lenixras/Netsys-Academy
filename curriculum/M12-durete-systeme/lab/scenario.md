# Labo M12 — Dureté système : durcir un serveur neuf

**Objectif** : appliquer une checklist « CIS-lite » sur `host1` ( Debian, sans
systemd — tout se démarre à la main ) : SSH durci, politique de mots de passe,
umask, sauvegarde chiffrée-compressée, port SSH alternatif.

Terminal : bouton **Terminal** → nœud `host1` (root). Édition de fichiers :
onglet **Éditeur** (nœud `host1`, chemin absolu, ex. `/etc/ssh/sshd_config`).

## Étape 1 — Interdire le login root en SSH (2 pts)

Dans `/etc/ssh/sshd_config`, la ligne (non commentée) doit devenir :

```
PermitRootLogin no
```

En shell :
```bash
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
grep '^PermitRootLogin' /etc/ssh/sshd_config      # doit afficher "PermitRootLogin no"
```

## Étape 2 — Compte admin2 avec politique d'âge (2 pts)

Créer l'utilisateur `admin2` puis imposer un âge minimum de **7 jours** et un
âge maximum de **90 jours** pour son mot de passe :

```bash
useradd -m -s /bin/bash admin2
chage -m 7 -M 90 admin2
chage -l admin2          # Minimum : 7 / Maximum : 90
```

## Étape 3 — umask durci pour admin2 (2 pts)

Un umask de `027` (ou `077`) empêche la fuite de droits vers « group/other ».
Le plus propre : un script dans `/etc/profile.d/`, source au login :

```bash
echo 'umask 027' > /etc/profile.d/99-hardening.sh
chmod 0644 /etc/profile.d/99-hardening.sh
su - admin2 -c umask     # doit afficher 0027 (ou 0077)
```

Attention : sans `su -` (login shell), `/etc/profile.d` n'est pas lu.

## Étape 4 — Sauvegarde compressée de /etc/passwd (2 pts)

Règle 3-2-1 (voir cours) : ici, première copie locale compressée. Le fichier
`/root/backup/etc-passwd.gz` doit exister et contenir la ligne `root:` :

```bash
mkdir -p /root/backup
gzip -c /etc/passwd > /root/backup/etc-passwd.gz
zcat /root/backup/etc-passwd.gz | head -1
```

## Étape 5 — SSH à l'écoute sur le port 2222 (2 pts)

Pas de systemd ici : on (re)démarre sshd à la main. Le démon doit être lancé
avec `-p 2222` (les clés d'hôte et le répertoire de privilèges doivent exister) :

```bash
mkdir -p /run/sshd
ssh-keygen -A               # génère les clés d'hôte si absentes
/usr/sbin/sshd -p 2222      # se détache en arrière-plan
ss -tln | grep ':2222'
```

Pour appliquer un changement de `sshd_config` : retrouver le PID avec
`ss -tlnp | grep ':2222'`, `kill <pid>`, puis relancer la commande ci-dessus.

## Vérification

Clique **Vérifier** : 10/10 attendu. Chaque check est en lecture seule
(`grep`/`chage -l`/`ss`), tu peux re-vérifier autant de fois que nécessaire.
