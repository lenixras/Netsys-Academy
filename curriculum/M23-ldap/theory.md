# M23 — LDAP : l'annuaire des identités

## Pourquoi un annuaire central ?

Gérer `useradd` sur 200 machines = cauchemar. **LDAP** (Lightweight Directory
Access Protocol) centralise les identités dans un arbre :

```text
dc=lab23,dc=local            ← la base (suffix)
├── ou=People                ← unité d'organisation
│   └── uid=elev1            ← une entrée = un objet (attributs typés)
```

Chaque entrée a un **DN** (nom complet), des **objectClasses** (le contrat :
quels attributs sont obligatoires — ici `inetOrgPerson`) et des attributs.

## Le protocole, sans les mythes

- Port 389 (ldap://) ou 636 (ldaps://) — en lab, on écoute sur 389 en clair.
- Un client fait un **bind** (s'identifie : `-D cn=admin -w secret`) puis un
  **search** (filtre `(uid=elev1)`).
- Les ajouts passent par des fichiers **LDIF** importés avec `ldapadd`.

## slapd sans systemd

Le paquet `slapd` fournit le daemon. Sans systemd dans le conteneur, on le
conduit à la main : un `slapd.conf` minimal (backend `mdb`, suffix, rootdn,
rootpw, dossier de données), puis :

```text
slapd -u openldap -g openldap -f /etc/ldap/slapd.conf -h ldap://10.23.0.10:389/
```

## Étapes du lab

1. Écrire `/etc/ldap/slapd.conf` (les includes des schémas core + cosine + inetorgperson
   sont obligatoires pour `inetOrgPerson`).
2. Lancer slapd sur 10.23.0.10:389.
3. Importer la base (`dc=lab23,dc=local`, `ou=People`, `uid=elev1`) avec
   `ldapadd` en tant que rootdn.
4. Vérifier depuis `cli` : `ldapsearch -H ldap://10.23.0.10 -x -b dc=lab23,dc=local`.
