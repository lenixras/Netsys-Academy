# M17 — Capstone : projet intégrateur

Vague 4. Prérequis : M0–M16.

## Objectifs
- Transformer un cahier des charges en conception réseau complète.
- Produire plan d'adressage, topologie, configs et tests de bout en bout.
- Industrialiser : Git, CI, documentation, automatisation (M15/M16).
- Tenir un barème : chaque exigence du sujet doit être **prouvable**.
- Soutenir ses choix techniques devant un jury.

## Théorie

### 1. Ce qu'évalue un capstone
Un projet intégrateur ne teste pas une compétence isolée : il teste la
**chaîne complète** — comprendre un besoin, le traduire en conception, la
réaliser, la vérifier, la documenter, la défendre. Les compétences
mobilisées viennent de tout le cursus : l'adressage (M8), la commutation
et les VLANs (M5), le routage (M6), les services (M4), le pare-feu (M11),
l'observabilité (M10), le durcissement (M12), l'automatisation (M14–M16),
la rigueur de dépannage (M13). Le barème reflète cet ordre : conception,
réalisation, vérification, documentation, soutenance.

### 2. Le cahier des charges → l'analyse
Un sujet type : « petite entreprise, 3 sites reliés, 150 postes filaires,
Wi-Fi visiteurs et employés, serveurs DMZ, accès Internet redondé,
supervision, sauvegarde des configs ». La première production est une
**matrice exigences → décisions** : chaque exigence (souvent floue) devient
un choix chiffré et justifié : nombre de VLANs et pourquoi ce découpage
(par fonction/confiance, pas par étage physique), tailles de sous-réseaux
(VLSM, M8), protocoles de routage (OSPF par site, statique/BGP vs
fournisseur), placement des services. Les non-dits du sujet (budget,
croissance, contraintes réglementaires) doivent être **explicités en
hypothèses écrites** — c'est noté.

### 3. Le plan d'adressage, pièce maîtresse
Avant toute topologie : le plan. Un bon plan tient dans un tableau :
préfixe, VLAN, nom, passerelle, usage, taille, croissance. Il respecte :
- agrégation hiérarchique (un préfixe parent par site, sous-préfixes par
  fonction — favorable à la convergence et aux ACL) ;
- réserves explicites (infra, interconnexions /31, loopbacks /32) ;
- contiguïté et absence de chevauchement (prouvé par script M14, vérifié
  par CI M16) ;
- alignement avec les VLANs (M5) et les ACL/feux (M11) : une règle doit
  nommer un segment du plan, jamais une IP isolée.

### 4. La topologie
Le plan devient graphe : containerlab (M16) ou equivalent, avec les nœuds
rôlés (switchs, routeurs FRR/VyOS, pare-feu nftables, serveurs de services,
AP si M9 pertinent). Points de conception à justifier au barème :
- **redondance** : liens up/down avec STP (M5), ECMP ou routes
  préférentielles (M6) — et ce que ça coûte ;
- **zones de confiance** : périmètre DMZ/internes/externes cohérent avec
  la politique du pare-feu (M11) ;
- **services critiques** : DHCP relay inter-VLAN (M4+M5), DNS/NTP
  internes (M4), observabilité présente partout (M10) ;
- **lisibilité** : nommage des nœuds, interfaces, adjacences ; un graphe
  que le jury ne comprend pas en 2 minutes est une faute de conception.

### 5. Les configurations : générées, pas tapées
L'échelle interdit le cliquage manuel : les configs sortent de templates
(M15) ou de netlab (M16), à partir du **plan d'adressage comme source de
vérité unique**. Le livrable attend la chaîne : plan → génération →
déploiement → vérification. Chaque équipement doit pouvoir répondre à «
d'où vient cette ligne ? » (commit Git). Le durcissement (M12) s'applique
aux nœuds : pas de root SSH, SNMP en v3 ou community isolée, logs vers le
collecteur.

### 6. Les tests de bout en bout
Le lot qui sépare un labo qui « semble marcher » d'un projet **prouvé** :
- connectivité : matrice ping attendue/autorisée (intra-VLAN oui, inter-
  zones selon la politique) ;
- routage : tables OSPF complètes, convergence après coupe d'un lien ;
- services : obtention de bail via relay, résolution DNS, horodatages
  synchrones ;
- sécurité : ce qui doit être bloqué l'est (DNAT publiés uniquement,
  scanning silencieux côté wan), ce qui doit être journalisé l'est ;
- observabilité : les métriques/traps des incidents de test atteignent le
  collecteur ;
- automatisation : rejouer `deploy + checks` depuis Git fonctionne sur une
  machine neuve.

Ces tests sont écrits dans le langage des checks de la plateforme (scripts
`docker exec` + regex, M5) ou en Python (M14) et font partie du dépôt ; la
CI (M16) les exécute.

### 7. Documentation et soutenance
Le dossier : cahier des charges reformulé, hypothèses, plan d'adressage,
schéma, extraits de configs **avec justification**, résultat des tests,
procédure de déploiement, post-mortem d'un incident volontairement injecté
et résolu (M13). La soutenance (15–20 min) : 5 min de conception, 10 min
de démonstration en direct sur un labo **rejouable**, 5 min de questions.
Critères du jury : le candidat sait défendre chaque chiffre (pourquoi /25
ici, pourquoi ce VLAN), connaît ses limites (« ce qui passerait en prod
réel »), et n'accuse pas l'outil pour un oubli de conception.

### 8. Piloter le projet : temps et risques
Un capstone se rend à date ; la conduite tient dans trois réflexes :
1. **jalons** : à J+1 le plan d'adressage figé, à J+2 la topologie déployée
   vierge, à J+3 les services montés, à J+4 les tests écrits — l'ordre
   protège des dérives (on ne dépanne pas une topologie qu'on n'a pas déployée) ;
2. **risques identifiés** : le DHCP inter-VLAN, le pare-feu qui se verrouille
   sur lui-même (lockout), la config générée qui diverge du plan — les trois
   pannes classiques d'un capstone, à tester en priorité ;
3. **budget de débogage** : se réserver une demi-séance de marge ; un
   projet sans marge finit en soutenance avec un labo cassé.

Un dernier garde-fou : la **checklist de rendu** relue la veille — chaque
exigence du sujet a une ligne « exigence / décision / preuve (test) / état
», et toute ligne sans preuve est soit complétée, soit explicitement
abandonnée dans le dossier.

## Bonnes pratiques / pièges
- **Concevoir d'abord, déployer ensuite** : un apprenant qui ouvre un
  terminal avant d'avoir figé le plan perd le barème conception et se
  retrouve avec un patchwork à recâbler.
- Ne pas sur-concevoir : un capstone de semaine n'a pas besoin de BGP +
  MPLS + SD-WAN ; le barème récompense la **cohérence**, pas l'empilement.
- Chaque exigence du sujet doit avoir une **preuve** dans les tests : ce
  qui n'est pas prouvable n'est pas rendu.
- Oublier le cas « le DHCP relay n'est pas configuré » (M4/M5) : panne
  n°1 des capstones — un VLAN sans relay n'a pas d'adresse.
- Sauvegarder/commiter **avant** chaque étape risquée ; le labo final
  doit être reproductible depuis le dépôt, pas depuis la mémoire du
  terminal.
- En soutenance, une démo qui échoue se reconnaît : répéter le déploiement
  complet la veille, sur une machine propre.
- La dernière ligne du barème est souvent la plus dure : les **limitations
  honnêtement écrites** valent mieux qu'un silence.

## TP — Projet complet noté sur barème
Le sujet est tiré d'une banque (exemples : « deux sites interconnectés,
IPSec/VPN option » ; « petit datacenter : DMZ + internes + supervision » ;
« rénovation d'un plan /23 existant en VLANs fonctionnels »). Rendu :
dépôt Git (topologie + configs générées + tests + docs) et soutenance.
Étapes évaluées par checks machine + jury :
1. **conception** (barème propre) : plan d'adressage validé par le script
   de vérification (pas de chevauchement, toutes les exigences couvertes) ;
2. **réalisation** : `clab deploy` du labo depuis le dépôt, checks de
   connectivité/services/politique passés en CI (M16) ;
3. **résilience** : incident injecté par l'examinateur (lien coupé, service
   arrêté) — le candidat dépanne en méthode (M13) sous chronomètre ;
4. **soutenance** : démonstration + questions, avec le dépôt comme source
   unique.

Le score final agrège checks automatiques (réalisation) et grille du jury
(conception/documentation/soutenance) ; il est poussé dans Moodle comme
chaque module.

## Critères de validation
- Quiz ≥ 70 % (questions de synthèse, pas de détail protocolaire).
- Projet noté sur barème + soutenance (checks machine sur la chaîne
  conception → déploiement → tests).
