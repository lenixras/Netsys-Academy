# Labo M2 — Linux de base : shell, filesystem, permissions, processus

**Objectif** : prendre en main le shell dans un vrai système de fichiers. Vous allez
créer une arborescence projet, écrire et exécuter un script, appliquer des permissions
précises, exploiter `find`/`grep` avec une redirection, et lancer un processus en
arrière-plan. Chaque étape produit un artefact que le bouton **Vérifier** contrôle.

- Nœud : `h1` (un seul). Vous êtes **root** dans le terminal web.
- Durée : ~30 min. Rien n'est préconfiguré : tout est à créer.
- L'environnement est un conteneur Debian **sans systemd** : pas de services ni de
  `journalctl`, tout se passe dans les fichiers et les processus.

## Étape 0 — Prise en main du terminal

Ouvrez l'onglet **Terminal** du lab (bouton `h1`). Déplacez-vous :

```bash
whoami
pwd
ls -l /
cd /root && pwd
```

`/` est la racine du filesystem, `~` le répertoire personnel de l'utilisateur courant
(ici `/root`). Note : les liens « réseau » (eth0/eth1) existent mais ne servent pas ici.

## Étape 1 — L'arborescence du projet

Créez d'un coup deux répertoires imbriqués avec `-p` :

```bash
mkdir -p /root/proj/bin /root/proj/logs
ls -l /root/proj
```

**Vérif** : le check `arborescence_proj` teste `test -d` sur `bin` et `logs`.

## Étape 2 — Un script exécutable avec l'éditeur intégré

Dans l'onglet lab, utilisez l'**éditeur de fichiers intégré** (bouton *Fichiers*,
nœud `h1`) : saisissez le chemin `/root/proj/bin/hello.sh` et collez :

```bash
#!/bin/bash
echo "bonjour depuis hello.sh"
```

Enregistrez. Puis, dans le terminal, donnez le droit d'exécution et testez :

```bash
chmod +x /root/proj/bin/hello.sh
/root/proj/bin/hello.sh
```

Sans `chmod +x`, l'exécution échoue (« Permission denied ») ; sans shebang
(`#!/bin/bash` en première ligne), l'interpréteur à utiliser n'est pas connu.

**Vérif** : `hello_executable` (test -x) et `hello_bonjour` (le script tourne et
affiche le mot-clé `bonjour`).

## Étape 3 — Un fichier de journal et des permissions exactes

Créez le journal avec exactement ce contenu (via l'éditeur, ou en terminal) :

```bash
cat > /root/proj/logs/access.log << 'EOF'
2026-01-10 08:01:22 INFO Service démarré
2026-01-10 08:03:45 ERROR Disque plein
2026-01-10 08:04:10 INFO Sauvegarde OK
2026-01-10 08:05:00 ERROR Timeout BDD
2026-01-10 08:06:30 ERROR Panne réseau
EOF
```

Puis appliquez les permissions attendues : **propriétaire en lecture/écriture, groupe
en lecture seule, rien pour les autres** — soit `640` en notation octale :

```bash
chmod 640 /root/proj/logs/access.log
stat -c %a /root/proj/logs/access.log     # doit afficher 640
ls -l /root/proj/logs/access.log          # doit afficher -rw-r-----
```

**Vérif** : `perms_access_log` compare la sortie de `stat -c %a` à `640`.

## Étape 4 — grep + redirection : le fichier compteur

Combien de lignes contiennent `ERROR` ? Comptez-les (`-c`) et **redirigez** le
résultat dans un fichier `erreur.txt` (`>` écrase le fichier, `>>` ajoute) :

```bash
grep -c ERROR /root/proj/logs/access.log
grep -c ERROR /root/proj/logs/access.log > /root/proj/logs/erreur.txt
cat /root/proj/logs/erreur.txt
```

Le check valide la **cohérence** : le nombre dans `erreur.txt` doit être exactement le
nombre de lignes `ERROR` de votre `access.log`. Explorez aussi le filesystem :

```bash
find /root/proj -type f
find /root/proj -name '*.log'
wc -l /root/proj/logs/access.log
```

**Vérif** : `compteur_erreurs`.

## Étape 5 — Un processus en arrière-plan

Lancez une « veilleuse » détachée du terminal : `&` envoie la commande en
arrière-plan, `nohup` la protège du signal de fermeture du terminal :

```bash
nohup sleep 4321 > /dev/null 2>&1 &
pgrep -f "sleep 4321"
ps aux | grep "[s]leep"
jobs
```

Notez `> /dev/null 2>&1` : on jette la sortie standard (1) **et** la sortie d'erreur
(2). Pour arrêter ce processus plus tard : `pkill -f "sleep 4321"`.

**Vérif** : `proc_background` (un processus dont la ligne de commande contient
`sleep 4321` doit exister).

## Étape 6 — Note finale

Cliquez **Vérifier** : 10 points répartis sur 6 checks. Relisez le cours
(`theory.md`) si un check manque — en particulier la notation octale des permissions
et le duo `nohup` + `&`.
