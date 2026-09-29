# Scénario — La migration IPv6 du labo

Votre labo a reçu le préfixe documentation `2001:db8:acad::/48` :
LAN1 = `:1::/64` (les machines), LAN2 = `:2::/64` (le serveur de calcul,
ici une adresse du routeur). Pas de DHCPv6 : la direction veut du SLAAC pur.

Objectifs :
1. Faire annoncer LAN1 par le routeur (radvd).
2. Vérifier que la machine h1 s'auto-configura (adresse SLAAC).
3. Atteindre LAN2 depuis h1 avec une route statique v6.
4. Rejouer le « ping » de toujours : `ping -6`, en gardant un oeil sur
   `ip -6 neighbor` (l'équivalent de l'ARP, en plus propre).
