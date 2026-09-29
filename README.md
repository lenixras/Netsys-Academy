# netsys-academy

Apprends les **réseaux** et les **systèmes** en faisant : 27 modules du niveau
débutant à expert (Cours → Quiz → Labo virtuel → Vérification automatique),
avec de vrais équipements réseau dans ton navigateur. 100 % gratuit, 100 %
auto-hébergé sur ta machine — aucune donnée ne sort de ton ordinateur.

## Ce que tu obtiens

- Un **site local** (`http://localhost:8090`) : catalogue des modules, progression et score par module.
- Un **terminal dans le navigateur** pour Configurer de vrais routeurs, switches et serveurs Linux.
- Des **labs interactifs** façon GNS3 : glisse les machines, câble-les, modifie la topologie.
- Un bouton **✔ Vérifier** qui note ton travail automatiquement et donne un **indice** sur chaque erreur.
- Des thèmes couverts : TCP/IP, Linux, VLAN, routage OSPF/BGP, Cisco-like, IPv6, DNS, DHCP,
  LDAP, mail, pare-feu, Wi-Fi, monitoring Prometheus, automation Ansible… (capstone final : M17).

## Installation

Il te faut une machine **Linux** (ou **WSL2 sous Windows**) avec **Docker** installé.

```bash
./install.sh   # une seule fois : prérequis + images des machines de lab
./start.sh     # démarre la plateforme
```

Puis ouvre **http://localhost:8090** dans ton navigateur et choisis un pseudo.
Pour arrêter : `./stop.sh`.

`install.sh` peut être long la première fois (téléchargement des images Docker).
Il n'a pas besoin de `sudo`.

## Premiers pas

1. **Accueil** : les 27 modules classés par vagues (Fondamentaux → Système → Réseau →
   Exploitation & sécurité → Automatisation → Capstone). Ta progression est affichée
   (labs réussis, quiz, niveau estimé).
2. Clique un module → 4 onglets :
   - **📖 Cours** : la théorie, en simple, avec exemples de commandes.
   - **❓ Quiz** : QCM corrigé immédiatement avec explications.
   - **🧪 Labo** : la topologie du réseau. Clique une machine pour ouvrir son terminal,
     « Modifier la topologie » pour ajouter/câbler des machines, puis applique.
   - **🎯 Scénario** : l'exercice pas à pas à réaliser dans le labo.
3. termine le scénario → **✔ Vérifier** → score et indices. Le **meilleur score est
   sauvegardé**, même après redémarrage de la machine.
4. Quand tu as fini : **Détruire** le labo (ou laisse-le expirer tout seul après
   inactivité).

## Bon à savoir

- **2 labos maximum en même temps** (par défaut) : la plateforme tourne sur ta RAM
  (~4 Go libres recommandés). Ferme un labo avant d'ouvrir l'autre.
- Pas de Windows Server / Active Directory : la plateforme est 100 % logiciels libres.
- Tu peux changer quelques réglages avec des variables d'environnement avant `./start.sh` :
  `PORT=9000` (port du site), `NETSYS_MAX_SESSIONS=1` (moins de labos simultanés).

## Ça ne marche pas ?

| Problème | Solution |
|---|---|
| `start.sh` ne répond pas | `tail var/launcher.log` (le log du site) puis relancer `./stop.sh && ./start.sh` |
| Un labo ne se déploie pas | RAM saturée : détruis l'autre session ; vérifie que Docker tourne (`docker ps`) |
| `install.sh` échoue | Relance-le (les téléchargements reprennent) ; sur WSL2 suis `docs/runbook-wsl2.md` |
| Des machines de lab restent bloquées | Redémarre la plateforme : elle purge les orphelines au démarrage |

## Pour aller plus loin (docs techniques)

- `docs/runbook-wsl2.md` — préparation d'un hôte WSL2.
- `docs/lab-authoring.md` — écrire son propre labo.
- `docs/moodle-setup.md` — synchroniser les notes avec un Moodle.
- `docs/architecture.md` — comment ça marche à l'intérieur.
- Tests développeur : `uv run pytest -q` et `tests/e2e.py`.
