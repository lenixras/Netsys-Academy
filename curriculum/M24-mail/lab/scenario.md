# Scénario — « On monte notre mail interne »

Le labo veut sa messagerie interne : pas de cloud, un serveur `mx` pour le
domaine `mx.lab24.local`, et alice (compte système déjà créé) comme seule
boîte. Vous livrez SMTP entrant + lecture IMAP.

1. Configurer Postfix (hostname, mydestination, inet_interfaces, mynetworks)
   et démarrer le service — `ss -tln` doit montrer le 25.
2. Envoyer un premier message « sujet lab24 » pour alice.
3. Écrire la config Dovecot (IMAP sur 10.24.0.10, mbox dans /var/mail, PAM)
   et la démarrer.
4. Depuis `cli` : banner 220 + `curl -u alice:secret imap://10.24.0.10/`
   qui renvoie la boîte INBOX.

Post-mortem : quel paramètre postfix aurait rendu la machine silencieusement
muette à vos messages ?
