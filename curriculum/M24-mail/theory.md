# M24 — Mail : Postfix + Dovecot, le duo open source

## Le trajet d'un email

```text
expéditeur --SMTP:25--> serveur entrant (MX) --> boîte aux lettres
lecteur    --IMAP:143/993--> boîte aux lettres
```

- **SMTP** (Postfix) : protocole de *remise*. Le serveur « MX » accepte le
  message pour son domaine (`mydestination`).
- **IMAP** (Dovecot) : protocole de *lecture* — le client liste les dossiers
  et lit la boîte sans la déplacer.

## Postfix en 5 lignes de config

```text
myhostname     = mx.lab24.local
mydestination  = mx.lab24.local, localhost
inet_interfaces = all
mynetworks     = 10.24.0.0/24
```

`postconf -e` écrit ces paramètres, `newaliases` prépare les alias, puis
`postfix start` (pas de systemd ici). Une phrase résume la sécurité :
**jamais ouvert à tout le monde** (`mynetworks` strict) sinon votre serveur
devient un spammeur.

## Dovecot sans TLS, en lab

En prod : IMAPS 993 + certificats. Ici, `ssl = no` sur un LAN isolé
(Dovecot 2.4 accepte les mots de passe en clair sans TLS sur ce port). La boîte est un **mbox**
classique dans `/var/mail/<user>` ; l'auth passe par PAM (users système).

## Étapes du lab

1. `mx` : configurer et démarrer postfix ; `echo "sujet lab24" | sendmail alice@mx.lab24.local`.
2. `mx` : écrire /etc/dovecot/dovecot.conf et lancer `dovecot`.
3. `cli` : vérifier le banner `220`, puis `curl -u alice:secret imap://10.24.0.10/`
   → la boîte INBOX doit apparaître.
