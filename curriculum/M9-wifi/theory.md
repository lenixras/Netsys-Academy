# M9 — Wi-Fi (802.11)

Vague 2. Prérequis : M1, M5.

## Objectifs
- Situer les bandes 2,4 / 5 / 6 GHz et leurs canaux.
- Relier norme 802.11 (a/b/g/n/ac/ax), largeur de canal et débit réel.
- Expliquer association, authentification et chiffrement WPA2/WPA3.
- Décrire le roaming et les mécanismes 802.11k/v/r.
- Établir un plan d'implantation (site survey) défendable.

## Théorie

### 1. La famille 802.11
Le Wi-Fi est la famille **IEEE 802.11** ; les noms marketing suivent les
amendements :

| Norme | Bande | Année | Apport |
|-------|-------|-------|--------|
| 802.11a | 5 GHz | 1999 | OFDM, moins de portée |
| 802.11b/g | 2,4 GHz | 1999/2003 | 11/54 Mbit/s, très porté |
| 802.11n (Wi-Fi 4) | 2,4 + 5 | 2009 | MIMO, canaux 40 MHz |
| 802.11ac (Wi-Fi 5) | 5 GHz | 2013 | VHT, 80/160 MHz |
| 802.11ax (Wi-Fi 6) | 2,4 + 5 (6E : 6 GHz) | 2021 | OFDMA, densité |
| 802.11be (Wi-Fi 7) | toutes | 2024 | 320 MHz, MLO |

Débit théorique ≠ débit réel : en 802.11 le support est **partagé**
(CSMA/CA), half-duplex par nature ; comptez 40–60 % du phy rate en trafic
utilisateur, et moins encore à plusieurs clients.

### 2. Bandes et canaux
- **2,4 GHz** (2,400–2,483 GHz) : bonne portée/pénétration, mais peu de
  canaux non chevauchants : en 20 MHz, seuls **1, 6, 11** (Europe : 1–13).
  Cohabitation avec four micro-ondes, Bluetooth, Zigbee → interférences.
- **5 GHz** : canaux nombreux (UNII-1/2/2e/3 : 36–64, 100–144 DFS, 149–165),
  débits élevés, portée moindre. Les canaux **DFS** (radar) imposent écoute
  préalable et éviction automatique — à éviter pour une borne de secours.
- **6 GHz** (Wi-Fi 6E) : bande large, aucun client legacy ; réglementaire
  (pas de radar, mais contrôle de puissance AFC aux USA).

Le **plan de canaux** d'un parc : réutiliser 1/6/11 en 2,4 GHz et un motif
36/40/48… ou 149/153/157 en 5 GHz en alternant, sans co-canal adjacent.

### 3. Trame et accès au support
802.11 utilise des adresses **MAC** (comme Ethernet, EtherType) mais avec
jusqu'à 4 adresses par trame (Retry, To/From DS) — car le lien sans fil est
logiquement en étoile : une trame client→serveur passe par l'**AP**, qui la
re-émet sur le distribution (lien souvent Ethernet + VLAN, retour du M5).
L'accès est **CSMA/CA** : écoute, fenêtre aléatoire (backoff), acquittement
obligatoire à chaque trame (pas de détection de collision : on ne peut pas
émettre et écouter en même temps). Conséquences : plus de clients = plus de
contention ; un client bas signal monopolise l'air (à gérer par
*airtime fairness* ou taux minimum).

### 4. Association et sécurité
- Découverte : balises **beacon** (SSID, capacités) émises périodiquement
  (102,4 ms) + sondes actives (Probe Request).
- Association : la connexion L2 au BSS (les 4 adresses MAC s'installent).
- **Ouverte** n'est pas **non chiffrée** en pratique : WEP (cassé, interdit),
  WPA/TKIP (déprécié), **WPA2-Personal (PSK)** = pré-partagé + AES-CCMP,
  **WPA3-Personal** = **SAE** (Dragonfruit : impossible de capturer/valider
  hors-ligne le handshake, password confirm) ; en entreprise : **WPA2/3-
  Enterprise (802.1X)** = EAP via **RADIUS** (FreeRADIUS, NPS) avec
  identités individuelles ; **OWE** pour les réseaux ouverts chiffrés.
- Une PSK partagée = un seul secret pour tous : fuite = tout le parc à
  refaire ; 802.1X = révocation individuelle.

### 5. Roaming
Le roaming est **piloté par le client** : il quitte un BSS pour un autre
(même SSID, même security) quand le signal du courant tombe sous un seuil
RSSI. Aides réseau : **802.11k** (mesures voisines : le client ne scanne
plus à l'aveugle), **802.11v** (gestion radio, steering 5/6 GHz),
**802.11r** (fast BSS transition, pré-calcul SAE/PMK pour roaming sans
nouvelle 802.1X). Bon roaming = RSSI min de bascule (-65 à -67 dBm),
cellules qui se recouvrent ~20 %, canaux non co-canaux, mêmes paramètres
de sécurité. Un contrôleur ou un RADIUS partagé (802.1X) doit être
reachable pendant la bascule.

### 6. Plan d'implantation (méthode)
1. Recueillir : plans des locaux, matériaux (béton/bardage métallique =
   atténuation forte), usage (voix = -67 dBm partout, data = -75), densité.
2. Pré-étude sur plan : placement AP en quinconce, puissance initiale
   moyenne, 2,4 GHz limité aux besoins IoT.
3. **Site survey** actif (mesure terrain : heatmap RSSI/SNR, co-canaux).
4. Ajuster canaux/puissances ; vérifier la capacité (clients/AP, airtime).
5. Documenter : plan, table AP→IP→VLAN→canal→puissance.

### 7. HwSim : le labo (quand l'hôte le permet)
`mac80211_hwsim` (module noyau) simule des radios 802.11 : plusieurs `wlan`
virtuels + un AP géré par **hostapd** (SSID, WPA3-SAE, canal) et des clients
**wpa_supplicant**. C'est le vrai supplicant, le vrai SAE, le vrai
roaming — mais ce module n'est pas disponible sur tous les hôtes (WSL2) :
le TP de ce module est donc un **drill de plan d'implantation** sur données
fournies.

### 8. Mesurer la qualité radio
L'observabilité Wi-Fi se lit par indicateurs :
- **RSSI** (dBm reçu) : au-delà de -65 dBm pour de la voix, -75 pour de la
  data confortable ; en dessous de -80, le client décroche ou tombe à des
  taux bas ;
- **SNR** (RSSI − bruit) : > 25 dB pour du haut débit ; le bruit monte avec
  le nombre de sources (voisins, IoT 2,4 GHz) — un canal propre vaut mieux
  qu'un AP de plus ;
- **taux de réémission / airtime** : les AP mesurent la charge du canal
  (channel utilization) : au-dessus de ~60–70 %, la latence explose même
  avec des clients proches ;
- **compteurs par client** : `iw dev wlan0 station dump` donne RSSI, débit
  de liaison (tx bitrate), erreurs — le premier endroit où regarder un
  client qui « rame ».
Réglages qui se mesurent : puissance (couvrir sans hurler), taux minimaux
dusés (désactiver les 1–2 Mbit/s pour ne pas brider l'airtime), band
steering (privilégier 5/6 GHz), seuils de bascule de roaming. Un plan
d'implantation est validé par ces chiffres terrain, pas par les promesses
marketing des « Mbit/s max ».

## Bonnes pratiques / pièges
- Ne pas couvrir « à fond de balle » : un AP à puissance max attire des
  clients loin qui ne peuvent pas répondre (asymétrie downlink/uplink) et
  brouille les voisins — la couverture se règle pour que le **client**
  parlant le plus fort atteigne l'AP.
- SSID unique ≠ roaming : il faut mêmes bande/paramètres et recouvrement.
- Désactiver le 2,4 GHz par réflexe est une erreur : l'IoT et les vieux
  clients y vivent ; le masquer est souvent la bonne réponse.
- WPA3 : prévoir la transition (PSK mixte) le temps du parc ; WPA3-Enterprise
  = cryptographie plus robuste (CNP) mais 802.1X reste la vraie sécurité.
- Ne jamais brancher un AP « maison » non déclaré (rogue) : il casse le
  plan de canaux et ouvre une porte — la détection de rogue est un point de
  contrôle (M10/M12).
- Un échec d'association vient souvent d'un mot de passe correct mais
  d'une **négociation de gestion de clés** refusée (client legacy bloquant,
  PMF requis avec un client qui ne le gère pas : `ieee80211w=1` vs `=2`).

## TP — Plan d'implantation Wi-Fi (drills)
Le TP est un drill sur fichier (cohérent avec le labo annoncé) : l'apprenant
reçoit un plan de locaux simplifié (briques de pièces,
matériaux, usage) et une liste d'AP. Checks machine sur vos réponses :
1. placer les AP : nombre minimal et positions (couverture -67 dBm cible
   en zones voix, en tenant compte de l'atténuation fournie) ;
2. affecter les canaux 2,4/5 GHz sans co-canal adjacent (le script vérifie
   le motif sur votre tableau) ;
3. choisir le mode de sécurité par SSID (invité = PSK ouverte-avec-OWE ou
   portal, employés = 802.1X/RADIUS sur VLAN dédié) ;
4. calculer le budget de capacité : 60 clients sur 3 AP, débit moyen
   d'association — est-il légitime, seuils de bascule ;
5. diagnostiquer un cas : « le portable roam sans cesse entre AP3 et AP4 »
   (réponse attendue : recouvrement asymétrique / seuils / puissance).

Les checks machine évaluent les valeurs saisies dans les fichiers de
réponse du drill (score JSON standard).

## Critères de validation
- Quiz ≥ 70 %.
- TP vérifié par script (checks machine sur le drill de plan d'implantation).
