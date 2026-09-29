# Labo M15 — Ansible : piloter `tgt` depuis `ctl`

**Objectif** : mettre en place le couple contrôleur/cible (SSH + clés), écrire
inventaire + playbook, et les exécuter depuis `ctl`. Réseau de service :
`ctl` = **10.15.0.1/24**, `tgt` = **10.15.0.2/24** sur `eth1` (configuré par le
setup). Sur `tgt`, sshd tourne et le mot de passe root est `ansible` (setup).

## Étape 1 — Clé SSH depuis ctl (prérequis du ping Ansible)

Terminal web → nœud `ctl` :

```bash
mkdir -p /root/.ssh && chmod 700 /root/.ssh
ssh-keygen -q -t ed25519 -N '' -f /root/.ssh/id_ed25519
cat /root/.ssh/id_ed25519.pub        # copie la ligne affichée
```

Deux options pour livrer la clé publique à `tgt` :

- **via le terminal** (authent interactive OK, le terminal web est un vrai PTY) :
  ```bash
  ssh-copy-id -o StrictHostKeyChecking=no root@10.15.0.2   # mot de passe : ansible
  ```
- **via l'Éditeur de fichiers** : ouvre le nœud `tgt`, chemin
  `/root/.ssh/authorized_keys`, colle la ligne publique, sauvegarde.

Test : `ssh -o StrictHostKeyChecking=no root@10.15.0.2 hostname` doit répondre
`tgt` **sans demander de mot de passe**.

## Étape 2 — Inventaire

Éditeur (nœud `ctl`, `/root/inventory.ini`) :

```ini
[managed]
tgt ansible_host=10.15.0.2
```

Et un `/root/ansible.cfg` pour ne pas être interrompu par la vérification de
clé d'hôte :

```ini
[defaults]
inventory = /root/inventory.ini
host_key_checking = False
```

## Étape 3 — Premier ping

Depuis `ctl` (toujours `cd /root` pour charger `ansible.cfg`) :

```bash
cd /root && ansible -i inventory.ini all -m ping
# tgt | SUCCESS => {"changed": false, "ping": "pong"}
```

Si `UNREACHABLE` : vérifie la clé (`ssh ... hostname`), `ip addr` sur les deux
nœuds, puis `host_key_checking`.

## Étape 4 — Playbook `site.yml`

`/root/site.yml` (les fichiers de référence sont dans `lab/files/` du dépôt) :

```yaml
---
- name: Base systeme cible
  hosts: all
  remote_user: root
  tasks:
    - name: Creer le service account svcapp
      ansible.builtin.user:
        name: svcapp
        system: true
        shell: /usr/sbin/nologin
        create_home: false

    - name: Ecrire /etc/motd
      ansible.builtin.copy:
        dest: /etc/motd
        content: "Managed by Ansible\n"
        mode: "0644"
```

Exécuter : `cd /root && ansible-playbook -i inventory.ini site.yml`
→ `changed=2` (ou `ok=2` au second passage : c'est l'idempotence, la grande
vertu d'Ansible).

## Étape 5 — Contrôler le résultat sur tgt

Terminal web → `tgt` :

```bash
id svcapp
cat /etc/motd        # « Managed by Ansible »
```

Puis **Vérifier** : 10 pts (svcapp 4, motd 3, `ansible all -m ping` 3).
