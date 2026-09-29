# Scénario — L'école ouvre son annuaire

L'école (dc=lab23,dc=local) veut une seule liste d'identités : les élèves,
le personnel, et plus tard le Wi-Fi 802.1X. Vous posez le serveur pilote :
`srv` héberge l'annuaire LDAP, `cli` joue le poste d'admin.

1. Créer la config slapd (mdb, suffix dc=lab23,dc=local, rootdn cn=admin…).
2. Démarrer slapd sur 10.23.0.10:389.
3. Importer la base + un premier utilisateur (uid=elev1, mot de passe elev1pass).
4. Prouver depuis `cli` une recherche anonymes sur `(uid=elev1)` et un
   bind admin qui aboutit.

Question post-mortem : pourquoi l'annuaire refuse-t-il l'attribut `uid`
si les schémas ne sont pas chargés ?
