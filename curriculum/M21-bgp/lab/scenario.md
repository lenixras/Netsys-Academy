# Scénario — Les deux datacenters veulent se joindre

Votre entreprise (AS 64512, LAN 10.21.1.0/24 derrière r1) vient de louer une
baie chez un voisin (AS 64513, LAN 10.21.2.0/24 derrière r2). Un seul lien
les relie (10.0.21.0/29, vos IP .1 et .2 déjà posées).

Le plan d'adressage des LAN et des passerelles est déjà appliqué. À vous :
1. Ouvrir la session eBGP entre les deux AS.
2. Annoncer à chaque AS son LAN.
3. Prouver la jointure : h1 (10.21.1.10) ping h2 (10.21.2.10), et les routes
   BGP installées dans le noyau des deux routeurs.
