# Labo M1 — Modèle OSI & encapsulation : analyser des captures réelles

**Objectif** : comprendre l'encapsulation Ethernet → IP → TCP/UDP → DNS en
disséquant trois captures réseau fournies dans le sandbox, avec `tshark`, puis
remettre vos réponses dans des **artéfacts** (fichiers) que la plateforme compare
à l'analyse vivante des pcap.

## Ce qui est déjà en place

À l'ouverture de la session, le nœud `h1` contient trois captures :

| Fichier | Contenu |
|---|---|
| `/root/cap_tcp.pcap` | une connexion HTTP : handshake TCP complet (SYN, SYN/ACK, ACK) entre `10.1.1.10:51234` et `10.1.1.20:80` |
| `/root/cap_dns.pcap` | une requête DNS `www.netsys.test` (A) et sa réponse, en UDP/53 |
| `/root/cap_arp.pcap` | une requête ARP « qui a 10.1.1.20 ? » diffusée (`ff:ff:ff:ff:ff:ff`) |

Un dossier `/root/resp/` attend vos réponses. Ouvrez le **terminal web** (clic sur
le nœud `h1`) pour travailler, et l'**éditeur** intégré pour écrire les fichiers.

## Mini-cours express — lire une capture

```bash
tshark -r /root/cap_tcp.pcap            # vue résumé : 1 ligne par trame
tshark -r /root/cap_tcp.pcap -V         # verbeux : arbre complet L1..L7, trame par trame
tshark -r /root/cap_tcp.pcap -x         # hexdump brut (compter les octets à la main)
```

Filtres d'affichage utiles (`-Y`) :

```bash
tshark -r /root/cap_tcp.pcap -Y 'tcp.flags.syn==1 && tcp.flags.ack==0'   # les SYN seuls
tshark -r /root/cap_dns.pcap -Y 'dns.flags.response==0'                  # les requêtes DNS
```

Extraire un champ précis (`-T fields -e <champ>`) — c'est CE rendu-là qu'on attend :

```bash
tshark -r /root/cap_tcp.pcap -T fields -e tcp.flags
```

Chaque en-tête s'empile dans le précédent : en-tête Ethernet (14 octets, type `0x0800`
ou `0x0806`), en-tête IPv4 (`45` = version 4, IHL 20 o), en-tête TCP (`0x50` =
offset 20 o) ou UDP, puis la charge utile (payload DNS…). Regardez `-V` pour
retrouver cette emboîture, et la taille `frame.len` en octets sur le câble.

## Consignes — 6 artefacts à produire

Créez les fichiers suivants dans `/root/resp/`. **Une seule ligne, sans espace
superflue**, avec exactement la valeur que `tshark` calcule (les checks comparent
votre fichier à l'analyse vivante de la capture — pas de valeur « devinée ») :

1. `/root/resp/syn.txt` — nombre de trames **SYN sans ACK** dans `cap_tcp.pcap`.
   Astuce : `... | wc -l`.
2. `/root/resp/synack.txt` — nombre de trames **SYN+ACK** dans `cap_tcp.pcap`.
3. `/root/resp/seq.txt` — la **séquence des drapeaux TCP** des 3 trames, dans
   l'ordre, séparés par des virgules, tels que rendus par
   `tshark -r /root/cap_tcp.pcap -T fields -e tcp.flags | paste -sd,`
   (ex. `0x0002,...`). C'est la signature du handshake complet.
4. `/root/resp/arp_len.txt` — la **taille sur le câble** (`frame.len`, en octets)
   de la première trame de `cap_arp.pcap`. Comptez : en-tête Ethernet 14 + ARP 28.
5. `/root/resp/dns_q.txt` — le **nom queried** de la requête DNS
   (`dns.qry.name`, réponse non incluse).
6. `/root/resp/dns_id.txt` — l'**identifiant de transaction DNS** (`dns.id`) de
   cette requête, recopié **exactement** tel que `tshark` le rend (avec ou sans
   préfixe `0x` : faites le pipeline, ne devinez pas).

Brouillon autorisé, solution honnête obligatoire : vous pouvez générer les
fichiers directement avec les pipelines tshark vus ci-dessus.

Exemple complet :

```bash
tshark -r /root/cap_tcp.pcap -Y 'tcp.flags.syn==1 && tcp.flags.ack==0' | wc -l > /root/resp/syn.txt
```

## Validation

Quand les 6 fichiers sont en place, cliquez **Vérifier** : chaque check relit la
capture dans le conteneur et compare. 10 points au total ; le handshake complet
(2 pts), la taille de trame (2 pts) et les deux champs DNS (2+2 pts) pèsent le
plus lourd. Puis retournez lire `theory.md` pour ancrer les couches OSI.
