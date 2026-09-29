# M21 — BGP : le protocole d'Internet

## À quoi sert BGP ?

OSPF (M6) fait parler les routeurs **d'une même organisation** (un « AS »).
BGP relie les organisations entre elles : FAI, grandes entreprises, datacenters.
Chaque AS possède un **numéro d'AS** (ex. 64512) et annonce ses **préfixes**
(« mes réseaux sont 10.21.1.0/24 ») à ses voisins, appelés **pairs** (*peers*).

## eBGP en 5 commandes

Sur r1 (AS 64512), parler à r2 (AS 64513) :

```text
router bgp 64512
 neighbor 10.0.21.2 remote-as 64513
 address-family ipv4 unicast
  network 10.21.1.0/24
```

- `neighbor ... remote-as` = qui est mon voisin et son AS.
- `network ...` = mes préfixes, **seulement s'ils existent déjà dans la table**
  (ici connectés via eth2).
- FRR utilise les *address-families* ; Cisco IOS place `network` sans ce niveau.
- FRR **bloque par défaut** l'échange eBGP sans politique configurée (`ebgp-requires-policy`) : sur un lab sans route-map, ajoutez `no bgp ebgp-requires-policy` — IOS, lui, annonce par défaut.

## Pourquoi « Established » ?

La session TCP (port 179) doit s'établir ; les colonnes de
`show bgp summary` : état = Established et compteur de préfixes reçus.
Un voisin bloqué en `Active` = IP injoignable, AS numéro trompé, ou route
manquante vers le pair.

## Le chemin, pas la distance

BGP ne choisit pas « le moins de sauts » : il choisit selon la **politique**.
L'attribut central est l'**AS_PATH** : la liste des AS traversés. En pratique :
préfixe appris par un voisin du même AS (iBGP) → préféré, sinon le plus court
AS_PATH, etc. Un `local-pref` ou un `MED` peuvent tordre la sélection —
c'est exactement ce que les opérateurs vendent (« le transit moins cher »).

## Étapes du lab

1. Sur chaque routeur : `router bgp <mon-as>` + `neighbor <pair> remote-as <leur-as>`.
2. Annoncer son LAN avec `network` dans l'address-family ipv4 unicast.
3. Vérifier `show bgp summary` (Established), `show ip route bgp` (les routes),
   puis ping h1 → h2.
