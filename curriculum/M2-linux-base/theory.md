# M2 — Linux de base : shell, filesystem, permissions, processus

> Vague 1 · Prérequis : M1 · Travaux pratiques : labo `m2-shell` (nœud `h1`, 30 min)

## 1. À quoi sert un shell ?

Le **shell** est à la fois un programme et un langage : il lit une ligne de texte,
la découpe en *commande + arguments*, exécute le programme demandé, puis affiche la
sortie. Bash et dash (le `sh` de Debian) sont les interpréteurs les plus courants.

Dans notre plateforme, le terminal web est un shell **dans le conteneur du nœud** :
chaque frappe part par WebSocket vers un PTY (`docker exec`), comme si vous étiez
branché sur la machine. Vous y êtes root : pas de `sudo` nécessaire, mais attention,
une bêtise de suppression est possible (le lab est jetable, relançable).

Anatomie d'une ligne :

```
ls    -l    /root/proj
│     │     │
│     │     └─ argument (opérande) : sur quoi agir
│     └─────── option : comment agir (liste longue)
└───────────── nom du programme
```

Les options courantes se combinent (`ls -l -a` = `ls -la`) et certains arguments sont
obligatoires (`mkdir` sans nom de répertoire est une erreur).

## 2. Le filesystem : une arborescence, pas des disques

Linux voit **un seul arbre** raciné à `/` (le *virtual filesystem*, FHS) :

| Répertoire | Contenu attendu |
|---|---|
| `/bin`, `/usr/bin` | exécutables des commandes |
| `/etc` | configuration **textuelle** des services et du système |
| `/home/<user>` | répertoires personnels des utilisateurs |
| `/root` | home du superutilisateur (UID 0) |
| `/var` | données variables : logs (`/var/log`), spools |
| `/tmp` | fichiers temporaires effacés au reboot |
| `/proc`, `/sys` | vues virtuelles du noyau : processus, paramètres (voir M3/M5) |
| `/dev` | fichiers-périphériques (disques, terminaux) |

### Chemins absolus et relatifs

- **Absolu** : commence par `/` — invariant quel que soit l'endroit où l'on se trouve
  (`/root/proj/bin/hello.sh`).
- **Relatif** : interprété depuis le répertoire courant (`bin/hello.sh` vu depuis
  `/root/proj`). `.` = répertoire courant, `..` = parent.
- `~` = home de l'utilisateur courant (`/root` quand on est root).

Commandes de navigation : `pwd` (où suis-je ?), `cd ..`, `cd /var/log`, `ls`, `ls -l`
(droits, taille, date), `ls -a` (fichiers cachés, préfixés par `.`), `cd` sans
argument = retour au home.

Compléter les chemins avec la touche **Tab** fait gagner un temps considérable et
évite les fautes de frappe ; c'est un vrai réflexe d'administrateur.

## 3. Créer, consulter, détruire

```bash
mkdir -p a/b/c      # crée l'arborescence complète, pas d'erreur si existant
cat fichier         # affiche tout le contenu
head -n5 fichier    # premières lignes ; tail -f : suit les ajouts (logs)
less fichier        # consultation paginée (q pour quitter)
cp src dst          # copie ; cp -r pour un répertoire
mv ancien nouveau   # déplace OU renomme
rm fichier          # supprime (définitivement : pas de corbeille)
rm -r rep/          # répertoire et contenu ; rm -rf / = l'erreur fatale
```

`rm -rf` est la commande la plus dangereuse du shell : une espace de trop placée
(`rm -rf /home/ user`) peut effacer un répertoire entier. Toujours relire avant d'entrer,
surtout quand on est root.

## 4. Permissions rwx : le modèle Unix

`ls -l` commence par 10 caractères :

```
-rw-r----- 1 root root  190 jan 10 08:01 access.log
││││││││││
│││││││││└─ autres : r=lecture w=écriture x=exécution
│││││││└┴── groupe
│││┴┴────── propriétaire (owner)
└────────── d = répertoire, - = fichier régulier, l = lien symbolique
```

Trois droits :

- **r** : lire le contenu (pour un répertoire : lister les noms).
- **w** : modifier (pour un répertoire : créer/supprimer des entrées).
- **x** : exécuter le fichier comme programme (pour un répertoire : *traverser*,
  donc `cd` et accéder aux fichiers qu'il contient). Un script sans `x` ne se lance
  pas avec `./script.sh` — mais reste lisible avec `cat`.

Modifier :

```bash
chmod 640 f          # notation octale : 3 chiffres = owner/groupe/autres
chmod u+x f          # notation symbolique : +x pour l'owner
chmod 755 d          # rwxr-xr-x : standard des répertoires
chown devops f       # changer propriétaire ; chown :staff f le groupe
```

Rappel de l'octal : `r=4`, `w=2`, `x=1` ; on additionne par colonne.
`6` = rw, `4` = r, `0` = aucun → `640` = `rw-r-----`. Le **umask** définit les
permissions par défaut des nouveaux fichiers (souvent 022 → 644).

## 5. Entrées/sorties, redirections et pipe

Chaque processus reçoit trois flux numériques : `0` stdin (entrée), `1` stdout
(sortie normale), `2` stderr (messages d'erreur). Le shell peut les rediriger :

```bash
echo "ligne" > f        # stdout vers f : ÉCRASE le fichier
echo "suite" >> f       # ajoute à la fin
cmd > f 2>&1            # sortie et erreurs dans f (2>&1 = dupliquer 2 vers 1)
cmd < f                 # stdin lu depuis f
cmd > /dev/null 2>&1    # tout jeter (silence)
cat a b > combiné       # fusionner
```

Le **pipe** `|` branche la stdout de la commande de gauche sur la stdin de celle de
droite, en chaînant les outils :

```bash
ps aux | grep python | wc -l
find /etc -name '*.conf' | xargs grep -l port
```

C'est la philosophie Unix : petits outils orthogonaux, composition par texte.

### Rechercher et filtrer

```bash
grep ERROR access.log          # lignes contenant ERROR
grep -c ERROR access.log       # nombre de lignes correspondantes (-i insensible)
find /root/proj -type f        # tous les fichiers réguliers de l'arborescence
find /var/log -name '*.log'    # par motif ; -mtime -1 : modifiés depuis 24 h
wc -l fichier                  # nombre de lignes (mots, octets avec -w -c)
```

`$(commande)` (**substitution de commande**) injecte la sortie d'une commande dans
une autre ligne : `echo "fichiers: $(find . | wc -l)"`.

## 6. Processus : avant-plan, arrière-plan, signaux

Un processus = programme en exécution, identifié par un **PID**. Le shell tient une
file de *tâches* (`jobs`), dont une seule au **premier plan** (elle bloque le
prompt, reçoit Ctrl-C).

```bash
sleep 60 &          # lance en arrière-plan : le prompt revient
jobs                # liste des tâches de CE shell
fg %1               # ramène la tâche 1 au premier plan ; Ctrl-Z : suspendre, bg : relancer détaché
nohup cmd > /dev/null 2>&1 &   # survit à la fermeture du terminal (ignore SIGHUP)
ps aux              # tous les processus, avec utilisateur et ligne de commande complète
pgrep -f "sleep 60" # rechercher par motif dans la ligne de commande (idéal pour scripting)
kill 1234           # envoyer SIGTERM (demande polie) ; kill -9 = SIGKILL (forcé, non filtrable)
pkill -f motif      # kill par motif
top                 # visionneuse temps réel (touche q pour quitter)
```

Ctrl-C envoie **SIGINT** au premier plan. Un processus en arrière-plan lancé sans
`nohup` meurt généralement à la déconnexion (SIGHUP) — c'est pourquoi le TP utilise
`nohup sleep 4321 &` que le check retrouve avec `pgrep`.

## 7. Paquets : dpkg et apt (théorie côté hôte)

Distribution Debian = système de **paquets**. Deux couches :

- `dpkg -l` : liste les paquets installés localement ; `dpkg -i paquet.deb` installe
  un fichier .deb (sans résoudre les dépendances).
- `apt` / `apt-get` : au-dessus de dpkg, résout les dépendances depuis des dépôts
  (`/etc/apt/sources.list`) : `apt update` (rafraîchir la liste), `apt install curl`,
  `apt remove`, `apt search`.

Dans la sandbox du lab, **ne pas `apt install`** : pas de persistance, réseau limité
aux miroirs selon l'hôte, et rien n'est requis pour le TP — tout l'outillage nécessaire
est déjà dans l'image `netsys/labnode:2`.

## 8. Spécificité de la sandbox (à savoir pour M3+)

Nos nœuds sont des **conteneurs** Debian : un seul espace de noms, un PID 1 minimal
(`sleep infinity`), **pas de systemd**. Conséquences :

- `systemctl`, `journalctl` ne fonctionnent pas → les logs se lisent dans `/var/log`
  ou se créent par redirection ; l'administration de services se fera par commandes
  directes et processus lancés à la main (cf. M3).
- `/etc`, `/proc`, `/sys` existent bel et bien : tout ce que vous apprenez ici est
  du vrai Linux, seulement sans l'orchestrateur de services.
- Chaque vérification (bouton **Vérifier**) exécute des commandes de lecture dans le
  nœud : ce qui compte est ce qui *existe réellement* (fichiers, permissions,
  processus vivants), pas ce que vous avez tapé dans l'historique.

## 9. Mémo express

| Besoin | Commande |
|---|---|
| où suis-je / qui suis-je | `pwd` · `whoami` |
| détailler les droits | `ls -l` · `stat -c %a f` |
| permissions exactes | `chmod 640 f` (octal r=4 w=2 x=1) |
| compter des lignes | `grep -c MOTIF f` |
| capturer une sortie | `cmd > f` / `cmd >> f` |
| tâche détachée | `nohup cmd > /dev/null 2>&1 &` |
| retrouver un process | `pgrep -f motif` · `ps aux \| grep motif` |
| paquets installés | `dpkg -l` |

Ensuite : quiz (≥ 70 % pour valider) et labo M2 — arborescence, script exécutable,
`chmod 640`, compteur grep, processus en arrière-plan. Le même ordre de commandes
que celui du `scenario.md` donne 10/10.
