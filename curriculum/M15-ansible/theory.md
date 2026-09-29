# M15 — Ansible : la config déclarative à grande échelle

## 1. Le problème qu'Ansible résout

Avec M14, vous savez automatiser UN équipement depuis UN script. À l'échelle
de 50 hôtes et 20 switchs, le script impératif (« connecte-toi, tape ces
commandes ») devient ingérable : pas de vision d'ensemble de l'état cible,
reprises hasardeuses, aucun historique. Ansible inverse la charge de la preuve :
vous **déclarez un état** (« tel utilisateur existe, tel fichier contient
tel contenu »), Ansible se charge de **converger** chaque cible vers cet état,
en ne changeant que le nécessaire.

Trois propriétés fondatrices :

- **agentless** : rien à installer sur les cibles — un serveur SSH et un
  Python suffisent (le module `ping` d'Ansible vérifie précisément cela,
  contrairement au ping ICMP) ;
- **idempotence** : relancer un playbook conforme ne change rien
  (`ok=…, changed=0`) ; c'est le critère de qualité n°1 d'un playbook ;
- **déclaratif YAML** : la syntaxe est verbeuse mais lisible en revue —
  un playbook est un document d'architecture autant qu'un programme.

## 2. Anatomie d'un projet Ansible

```
projet/
├── ansible.cfg        # options (inventory par défaut, host_key_checking…)
├── inventory.ini      # OU inventory/ (répertoire avec group_vars/…)
│   [managed]
│   tgt ansible_host=10.15.0.2
└── site.yml           # le playbook
```

### L'inventaire

L'inventaire décrit **qui existe** : hôtes, groupes, variables.

```ini
[managed]
tgt ansible_host=10.15.0.2

[managed:vars]
ansible_user=root
```

Un nom d'hôte peut être un simple alias : `ansible_host` porte l'adresse
réelle. Les variables d'inventaire (`host_vars/`, `group_vars/` en YAML)
alimentent les playbooks — c'est le début de la séparation « logique /
données » qui rend un playbook réutilisable.

### ansible.cfg

Le fichier de config lu quand on travaille dans le répertoire (d'où le
`cd /root` du labo). Les deux réglages utiles ici :

```ini
[defaults]
inventory = /root/inventory.ini
host_key_checking = False   # labo ; en prod, alimenter known_hosts proprement
```

## 3. Ad-hoc vs playbook

La commande ad-hoc, une tâche à la volée :

```bash
ansible all -m ping                        # module builtin ping → pong
ansible managed -m shell -a "uptime"       # module shell sur le groupe
ansible all -m copy -a "src=ntp.conf dest=/etc/ntp.conf"
```

Le playbook orchestre des **tâches** dans des **plays**, avec gestion d'erreur,
tags, handlers. Un play = des hôtes + des tâches ; une tâche = un module + ses
arguments + éventuellement `when`, `notify`, `register` :

```yaml
---
- name: Base système
  hosts: all
  remote_user: root
  tasks:
    - ansible.builtin.user:
        name: svcapp
        system: true
    - ansible.builtin.copy:
        dest: /etc/motd
        content: "Managed by Ansible\n"
      notify: recharger le cache        # handler déclaré plus bas
```

Le préfixe `ansible.builtin.` n'est pas décoratif : il ancre le nom du module
dans la collection officielle et évite les collisions avec des collections
communautaires. Les rôles (dossier `roles/`) factorisent des scénarios
complets — la suite Ansible Galaxy en fournit des milliers.

## 4. Les modules qui comptent pour un sysadmin réseau

| Module | Rôle | Idempotent |
|---|---|---|
| `ping` | test SSH + Python cible | — |
| `user` / `group` | comptes (état `present/absent`) | oui |
| `copy` / `template` | fichiers ; `template` = Jinja2 (variables → fichier) | oui |
| `lineinfile` / `blockinfile` | éditer une ligne/un bloc dans un fichier existant | oui |
| `package` / `apt` | paquets | oui |
| `service` / `systemd` | état du service (démarre/actif/rechargé) | oui |
| `shell` / `command` | escape impératif — dernier recours | non |
| `uri` | appels REST (configurateurs modernes) | selon méthode |
| `nftables`/`iptables` | règles pare-feu déclaratives | oui |

Règle d'équipe : chaque `shell` doit être justifié en revue — un playbook qui
fait `sed` dans un `shell` n'est plus déclaratif et casse l'idempotence
(il « change » à chaque passage).

### Handlers et variables

- `register: sortie` capture le résultat d'une tâche pour la consommer ensuite
  (`when: sortie.rc != 0`, boucles sur `sortie.stdout_lines`) ;
- un **handler** ne s'exécute qu'une fois, à la fin du play, si une tâche l'a
  notifié — le pattern « changer sshd_config → recharger sshd une seule fois » ;
- les **facts** (`ansible -m setup tgt`) donnent l'inventaire dynamique de la
  cible (IP, OS, disques) — exploitables dans les templates, base d'un
  CMDB léger.

## 5. SSH et secrets

Ansible se branche sur OpenSSH (transport `ssh`), donc tout le travail de M12
s'applique : clés déployées (étape 1 du labo), `sshd_config` durci, comptes
limités. Points spécifiques :

- `become: true` = élévation de privilèges via sudo (`ansible_become_pass`) ;
- le mot de passe de clé/du sudo se lit depuis un **vault** chiffré
  (`ansible-vault encrypt secret.yml`), jamais en clair dans l'inventaire ;
- en labo sans PTY interactif, `ssh-copy-id` demande le mot de passe : notre
  terminal web est un vrai PTY, ça marche — sinon, coller la clé publique dans
  `authorized_keys` (les deux méthodes documentées dans le sujet).

## 6. Exécution, puissance et limites

```bash
ansible-playbook -i inventory.ini site.yml            # tout le monde
ansible-playbook site.yml --limit tgt --check --diff  # dry-run + écarts
ansible-playbook site.yml --tags motd                 # sélectif
```

`--check` (et `--diff`) simulate l'exécution : indispensable avant une passe
de prod. La parallelisation (`forks`, défaut 5) et les `serial` par groupe
donnent la cadence.

Limites à connaître : Ansible ne connaît pas NAT ni cloisonnement L2 (d'où
les plans d'adressage des labs) ; les modules réseau fournisseurs passent par
des collections séparées (`ansible.netcommon`, `cisco.ios`…) avec `connection:
network_cli` (napalm/paramiko sous le capot) ; un playbook mal écrit devient
une boîte noire — d'où revues, linting (`ansible-lint`) et CI (M16).

## 7. Ce que vérifie le labo

Sur la topologie `ctl` ↔ `tgt` (10.15.0.0/24, mgmt clab-m15) :

1. `id svcapp` sur `tgt` (4 pts) — le play a convergé l'utilisateur ;
2. `grep "Managed by Ansible" /etc/motd` sur `tgt` (3 pts) — tâche `copy` ;
3. `ansible all -m ping` depuis `ctl` (3 pts) — clé SSH déployée, inventaire
   et config corrects.

Les fichiers de référence du sujet sont dans `lab/files/` du dépôt : comparez
votre copie en cas de doute — puis relisez chaque ligne pour comprendre
pourquoi elle est là.

## Références

- Docs Ansible : *Getting Started*, *User Guide* (variables, vault, roles).
- Collections réseau : `ansible.community.network`, `ansible.netcommon`.
- `man sshd_config`, `man ssh-copy-id` (revue M12).
