# Scénario — Le stage de remise à niveau réseau

Vous rejoignez une PME qui vient d'acheter des « switches Cisco » et un
« routeur Linux ». Le document d'archi promet : deux services (VLAN 10
Bureau, VLAN 20 Labo), un seul câble vers le routeur, et une config qui
survit au redémarrage.

Le switch est déjà programmé (VLANs + trunk). Il vous reste :

1. Créer les sous-interfaces VLAN du routeur.
2. Leur donner les adresses passerelles (192.168.10.254/24, 192.168.20.254/24) via vtysh.
3. Régler les deux postes (IP + passerelle) pour qu'ils se joignent.
4. Sauver la config du routeur (`write memory`) — l'auditeur de sécurité
   vérifiera que `show running-config` et le fichier sauvegardé concordent.

Ouvrez le terminal du routeur (clic sur le nœud r1) : `vtysh` vous attend,
avec le vocabulaire IOS que vous connaissez déjà.
