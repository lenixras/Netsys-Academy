# Labo M18 — Incident : l'intranet est mort 🎫

**Ticket ouvert à 08h42** : « Personne n'atteint `http://web.intranet.lab18` ce matin.
L'équipe infra a migré le serveur la semaine dernière (nouvelle IP **10.18.0.10**,
l'ancienne **10.18.0.99** est éteinte) et depuis rien ne marche. Le parc clients
obtient ses adresses en DHCP depuis ce même serveur. Rétablis le service. »

Deux machines : `srv` (DNS + web + DHCP) et `cli` (le poste d'un utilisateur).
Leur addressing de base est déjà en place : `srv` = 10.18.0.10/24, `cli` = 10.18.0.30/24
(sur eth1). Clique les nœuds de la topologie pour ouvrir les terminaux.

## Méthode support (à suivre dans l'ordre)

1. **Web** : sur `srv`, le serveur de fichiers ne tourne plus.
   `cd /root/www && nohup python3 -m http.server 80 > /root/www.log 2>&1 &`
   Vérifie : `ss -tln | grep :80`.
2. **DNS** : la zone est restée sur l'ancienne IP. Édite `/root/db.intranet.lab18` :
   `web IN A 10.18.0.10` (pense à augmenter le serial), puis relance
   `pkill -x named && named -c /root/named.conf -g > /root/named.log 2>&1 &`.
   Vérifie : `dig @10.18.0.10 web.intranet.lab18 +short`.
3. **Client** : la machine de l'utilisateur interroge encore un DNS fantôme.
   Corrige `/etc/resolv.conf` sur `cli` : `nameserver 10.18.0.10`.
   Vérifie : `getent hosts web.intranet.lab18`.
4. **DHCP** : le pool de `/root/dnsmasq.conf` est sur le mauvais sous-réseau.
   Mets `dhcp-range=10.18.0.100,10.18.0.150,255.255.255.0,1h`, valide avec
   `dnsmasq --test --conf-file=/root/dnsmasq.conf`.
5. **Clôture du ticket** : depuis `cli`, `curl http://web.intranet.lab18` doit
   afficher `OK`. Then **Vérifier** (10 pts, 5 checks) et consigne ton post-mortem
   dans `/root/postmortem.md` via l'éditeur de configuration.

## Ce que tu dois savoir expliquer à la fin

- Pourquoi une seule IP fantôme peut casser trois services différents.
- Ce que fait le serial d'une zone DNS et quand un rechargement est nécessaire.
- Ce que le `dnsmasq --test` valide — et ce qu'il ne valide pas.
