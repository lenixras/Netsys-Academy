# M25 — Monitoring avec Prometheus

## Le pull, pas le push

Prometheus **sonde** (*scrape*) chaque cible HTTP qui expose `/metrics` :
`node_exporter` publie CPU, mémoire, disques, réseau, au format texte
`node_cpu_seconds_total{cpu="0",mode="idle"} 123.45`. La cible n'envoie rien :
le collecteur passe la prendre. C'est le modèle « pull », plus tolérant aux
pannes des cibles.

## Les trois blocs d'une config

```yaml
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: tgt
    static_configs:
      - targets: ['10.25.0.20:9100']
```

- **job** : le nom qui apparaîtra dans les métriques (`up{job="tgt"}`).
- **up** : métrique interne = 1 si le scrape vient, 0 sinon. Le premier réflexe
  d'un admin : « mes cibles sont-elles up ? ».
- **PromQL** : le langage de requête (`up{job="tgt"}`, `rate(...)`…).

## Sans systemd

Les deux binaires se lancent à la main (en tâche de fond `&`) ; en prod
systemd ou k8s s'en charge. On garde la même philosophie : un process
exporter par machine, un serveur prometheus, et l'API HTTP pour tout vérifier.

## Étapes du lab

1. `tgt` : lancer `node_exporter` (listen 10.25.0.20:9100).
2. `mon` : écrire `/root/prometheus.yml` (job `tgt` vers `10.25.0.20:9100`) et
   lancer `prometheus`.
3. `mon` : vérifier `/api/v1/targets` (health up) puis la requête
   `up{job="tgt"}` dans `/api/v1/query`.
