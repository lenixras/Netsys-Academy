# Scénario — « Le DNS officiel doit survivre »

Le prestataire qui hébergeait votre DNS `lab22.local` coupe l'accès dans
30 jours. Vous dupliquez : `auth` (le maitre historique, déjà peuplé avec
web.lab22.local et son PTR) aura bientôt un secondaire `rec` — lui-même
aussi resolviseur des clients du LAN.

Votre mission avant le basculement :
1. Autoriser `auth` à transférer la zone vers `rec` (10.22.1.2), uniquement.
2. Sur `rec`, monter deux zones esclave (avant + inverse) et la récursion
   pour le LAN.
3. Depuis `cli`, prouver : `dig web.lab22.local` → 10.22.0.99 et
   `dig -x 10.22.0.99` → web.lab22.local, en passant bien par rec.
4. Bonus post-mortem : quel champ du fichier de zone déclenche la
   resynchronisation d'un secondaire ?
