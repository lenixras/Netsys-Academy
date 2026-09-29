# M12 — Dureté système & bonnes pratiques

## 1. Pourquoi durcir un système ?

Un serveur fraîchement installé est pensé pour être utilisable, pas pour être
sûr. Par défaut, il expose souvent : un accès root direct, des mots de passe
sans expiration, des fichiers créés lisibles par « group/other », des services
peu journalisés et un pare-feu absent. Le durcissement (« hardening ») consiste
à réduire cette surface d'attaque sans casser l'exploitation. Les références du
marché sont les **benchmarks CIS** et les baselines **NSA/CISA** ; elles se
lisent comme une checklist : identités, services, médias, audit, mise à jour.

Deux principes directeurs résument tout :

- **moindre privilège** : chaque compte, service et fichier obtient le strict
  nécessaire — ni plus, ni « au cas où » ;
- **défense en profondeur** : aucune mesure n'est suffisante seule ; un
  durcissement SSH n'aide pas si le mot de passe root est `admin`.

## 2. Durcir SSH

`sshd` est presque toujours le premier service exposé. Les réglages clés de
`/etc/ssh/sshd_config` :

| Directive | Effet |
|---|---|
| `PermitRootLogin no` | interdit la connexion directe en root : on se connecte en compte nommé, puis `sudo` — chaque action est rattachée à une identité |
| `PasswordAuthentication no` | n'accepte que les clés (après avoir déployé ses clés !) |
| `Port 2222` | déplace le service : **obscurcissement**, pas sécurité — mais supprime le bruit des botnets qui balayent le 22 |
| `MaxAuthTries 3` | coupe plus vite les tentatives par force brute |
| `AllowUsers` / `AllowGroups` | liste blanche d'identités autorisées |

Règle d'or : **ne jamais verrouiller la seule porte ouverte**. Testez une
seconde session avant de fermer la première, et gardez un accès console (ici,
le terminal web du labo joue ce rôle).

PAM (module d'authentification) ajoute la détection d'échecs : `pam_faillock`
(Débian/RHEL9+) ou `pam_tally2` (anciens) verrouille un compte après N échecs.
Un verrouillage temporaire (TAL) + une journalisation propre (`journalctl`,
`/var/log/auth.log`) donnent la visibilité nécessaire pour déboguer sans
deviner.

## 3. Identités et politique de mots de passe

Les âges de mot de passe se règlent par utilisateur avec `chage` :

```bash
chage -m 7  -M 90 admin2   # âge mini 7 j (anti « rotation vide »), maxi 90 j
chage -l admin2            # lecture de la politique
```

- **minimum** : empêche l'utilisateur de contourner l'historique en se
  ré-attribuant le même mot de passe dans la minute ;
- **maximum** : borne la fenêtre de validité d'un secret compromis ;
- `/etc/login.defs` porte les valeurs par défaut pour les comptes créés avec
  `useradd` ;
- `pam_history` (remember=5) et `pam_pwquality` (complexité) complètent.

L'umask, lui, décide des droits à la **création** de fichier. `umask 022`
(câblé par défaut) laisse `other` lire tout nouveau fichier ; `027` coupe
l'accès « other », `077` ne laisse que le propriétaire. Le point d'accroche
propre est un script dans `/etc/profile.d/` (sourcé par tout shell de login) :

```bash
echo 'umask 027' > /etc/profile.d/99-hardening.sh
```

À noter : les services démarrés hors login shell (cron, systemd) ne lisent pas
`/etc/profile.d` — chez eux, les droits se mettent dans le unit ou l'unité de
tâche. C'est le piège classique de l'umask « qui ne s'applique pas ».

## 4. Le MFA (multifacteur)

Un mot de passe, aussi fort soit-il, est « ce que vous savez ». Le MFA ajoute
un second facteur d'une autre nature :

- **ce que vous avez** : TOTP (jeton logiciel type freeotp/authenticator),
  clé matérielle FIDO2/WebAuthn ;
- **ce que vous êtes** : biométrie.

Le scénario de vol classique (phishing du mot de passe) échoue sans le second
facteur. Sous Linux, `libpam-google-authenticator` ou `pam_u2f` se branchent
sur la pile PAM de `sshd` (`AuthenticationMethods publickey,keyboard-interactive`).
Recommandation actuelle : les clés FIDO2 résistent au phishing, les TOTP non.

## 5. Sauvegardes : la règle 3-2-1

Durcir, c'est aussi savoir restaurer. La règle classique :

- **3 copies** de toute donnée importante (l'original + 2) ;
- **2 supports différents** (disque local + objet distant/NAS) ;
- **1 copie hors site** (sinon incendie/rançongiciel = tout perdu).

Compléments modernes : le **chiffrer** (une sauvegarde en clair sur un bucket
objet est une fuite potentielle), le **tester la restauration** (une
sauvegarde jamais restaurée est une croyance, pas une garantie), et la
règle des **3-2-1-1-0** (1 copie *immutable/air-gapped*, 0 erreur vérifiée).

Un backup « utile » est **versionné** : garder 7 J / 4 S / 12 M (les vieilles
sauvegardes ne s'écrasent pas). Et **métrologie** : un job de backup qui échoue
en silence n'existe pas — alertez à l'échec, pas au succès.

Pour un lab ou un petit serveur, une sauvegarde compressée suffit à montrer le
geste : `gzip -c /etc/passwd > /root/backup/etc-passwd.gz` — en production on
préfère `tar` + `gpg`, rsync versionné (restic, borg) ou snapshot du storage.

## 6. Mises à jour, pare-feu, journalisation

- **patching** : `unattended-upgrades` (Debian) pour le sécurité-only ;
  fenêtre de maintenance + plan de rollback pour le reste. Une vulnérabilité
  divulguée publiquement se exploite en heures : la SLA de patching se mesure.
- **pare-feu** : on n'expose que ce qui doit l'être (cf. module M11) ; ici
  l'équipement est minimal, mais la posture reste : default deny, règles
  nommées, test de la règle (voir M11 pour `nftables`).
- **journalisation** : auth, sudo, noyau. Sans log exploitable, la détection
  est impossible : on ne « voit » un incident que si on centralise (rsyslog →
  serveur de logs, cf. M10 observabilité).
- **auditer** : `auditd` sur les fichiers sensibles (`/etc/shadow`,
  `/etc/sshd_config`), `rpm -V` / `debsums` pour détecter les fichiers système
  modifiés.

## 7. Automatisation du durcissement

Une checklist appliquée à la main ne résiste ni au temps ni aux changements :
le serveur suivant sera plus ou moins durci. D'où les outils de « conformité »
que vous reverrez en M15/M16 :

- **Ansible / scripts** : appliquer la baseline (fichiers, paquets, services) ;
- **Lynis / OpenSCAP** : auditer le système contre une baseline et produire un
  score — le fameux « hardening index » ;
- **CI** : la baseline vit dans Git, chaque changement de config passe par une
  revue (cf. M16 IaC).

## 8. Ce que vérifie le labo

Cinq compétences, dix points, état réel vérifié par `docker exec` + grep :

1. `sshd_config` : ligne active `PermitRootLogin no` (2) ;
2. `admin2` créé, politique `chage` min=7 / max=90 (1+1) ;
3. umask effectif pour `admin2` : `su - admin2 -c umask` ∈ {027, 077} (2) ;
4. sauvegarde : `/root/backup/etc-passwd.gz` présent et contenant `root:` (2) ;
5. service : sshd à l'écoute sur 2222 (`ss -tln`) (2).

Rappel important : le conteneur tourne **sans systemd**. `systemctl` échoue,
tout se démarre à la main (`/usr/sbin/sshd -p 2222`), et un redéploiement de
session remet l'horloge à zéro : c'est volontaire, le durcissement doit être
reproductible — donc scriptable, donc versionnable. C'est le pont vers M15.

## 9. Erreurs classiques observées chez les stagiaires

- confisquer l'accès en appliquant `PasswordAuthentication no` **avant** d'avoir
  déployé la clé publique ;
- mettre `umask 077` dans `~/.bashrc` seulement (non appliqué aux shells non
  interactifs) et croire que tout est couvert ;
- sauvegarder `/etc/passwd` sans `/etc/shadow` — la sauvegarde est inutile pour
  restaurer l'authentification ;
- changer le port SSH et conclure « le serveur est sécurisé » ;
- oublier que le durcissement a un coût d'exploitation : chaque restriction
  doit avoir un processus de dérogation et un chemin de rollback testé.

## Références

- CIS Benchmarks — Distribution Independent Linux / Debian (gratuit pour usage personnel).
- NSA — *Hardening Ubuntu Server Operating System*.
- Fiszman, *UNIX and Linux System Administration Handbook* (chap. sécurité).
- `man 5 sshd_config`, `man 1 chage`, `man 5 profile`.
