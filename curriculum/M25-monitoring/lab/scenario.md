# Scénario — Le serveur de supervision du labo

Le chef d'atelier veut voir « d'un coup d'œil » si les machines vivent.
Vous installez le standard de fait : un hôte cible `tgt` avec son
**node_exporter**, et une machine `mon` qui héberge **Prometheus**.

1. Démarrer l'exporter sur `tgt` (port 9100, interface LAN).
2. Configurer le job `tgt` sur `mon` et démarrer prometheus (9090).
3. Prouver via l'API : cible 'health: up' et requête `up{job="tgt"} == 1`.
4. Question post-mortem : si `up` tombe à 0, quels trois réflexes ?
   (la cible répond-elle en HTTP ? le port ? le job pointe-t-il la bonne IP ?)
