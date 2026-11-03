# Assistant Emploi

Application web locale (Dash / Python 3) pour organiser une recherche d'emploi :
suivi des candidatures, gestion des versions de CV, statuts horodatés, commentaires,
copies locales des annonces, recherche filtrée, export ODS, statistiques et lettres
de motivation types. Thème sombre anthracite / ambre.

Les données restent **entièrement locales** (base SQLite dans `data/`).

## Fonctionnalités

- **Accueil** : CV actuel (téléchargement + versions antérieures), candidatures récentes
  en cartes (statut, CV utilisé, lien vers la copie locale de l'annonce, commentaires en
  bulles). Une alerte s'affiche si aucun CV n'est enregistré ; les candidatures sans CV
  valide sont marquées « CV inconnu ».
- **Recherche** : filtres par intitulé de poste, entreprise, statut et plage de dates.
- **Candidatures** : création / édition (tous les champs), suivi de **statut horodaté**
  (historique complet + statut courant), ajout de nouveaux types de statut depuis l'app,
  commentaires libres éditables (mise en forme du texte collé conservée, dates de
  création et de modification).
- **Contacts entrants** : appels, mails ou messages reçus de RH / chasseurs de têtes se
  saisissent dans la même fenêtre (champ « Type »), avec un champ « Contact » ; ils
  démarrent au statut « Contact reçu ».
- **Copies d'annonces** : si une URL http(s) est fournie, la page est enregistrée
  localement *après* l'enregistrement et consultable dans un nouvel onglet. Si la page
  téléchargée ne contient pas l'annonce (site en JavaScript, mur de cookies, blocage
  403), elle est rendue dans un Chromium headless (Playwright) qui accepte le bandeau
  de cookies ; les données structurées `JobPosting` servent de repli. Une copie douteuse
  ou un échec est signalé sur la carte avec sa raison. En dernier recours, le texte de
  l'annonce peut être collé à la main dans la fenêtre d'édition.
- **CV** : upload d'une nouvelle version (devient le CV actuel, les précédentes conservées).
- **Export ODS** : Date, Type, Poste, Entreprise, Contact, Dernier statut, URL.
- **Statistiques** : répartition par statut, activité des 30 derniers jours, candidatures
  par CV (pour repérer les meilleures versions).
- **Lettres de motivation** : création / lecture / modification / suppression, nombre de
  caractères calculé automatiquement.

## Démarrage rapide

```bash
pip install -r requirements.txt
playwright install chromium   # optionnel : annonces rendues en JavaScript
python run.py            # http://127.0.0.1:8050
```

Au premier lancement, une **base vide** est créée automatiquement. Rien d'autre n'est requis.

## Gestion de la base — `manage.py`

```bash
# Créer une base vide (aucune donnée)
python -m assistant_emploi.manage init

# Importer des candidatures depuis un tableur .ods (voir le format ci-dessous)
python -m assistant_emploi.manage import-ods --file mes_candidatures.ods [--cv mon_cv.pdf]

# Réinitialiser (vider la base)
python -m assistant_emploi.manage reset --force
```

### Format du tableur ODS pour l'import

Une ligne d'en-tête suivie des colonnes, dans cet ordre :

| Colonne | Contenu |
|---------|---------|
| n° | Ignoré |
| Date | `AAAA/MM/JJ`, `AAAA-MM-JJ` ou `JJ/MM/AAAA` |
| Offre | Intitulé du poste |
| Entreprise | Nom de l'entreprise |
| URL | URL de l'annonce **ou** moyen de candidature |
| État | Statut ; toute valeur ≠ statut par défaut crée un événement de statut |
| Commentaire | Si l'état n'est pas le défaut et que c'est une date → horodate le statut ; sinon devient un commentaire |

Les URLs http(s) déclenchent le téléchargement best-effort d'une copie locale
(`--no-download` pour l'éviter ; `--download-pending` pour réessayer les copies manquantes).

## Configuration — `config.json`

| Clé | Rôle |
|-----|------|
| `home_recent_count` | Nombre de candidatures récentes affichées sur l'accueil |
| `app_title` | Titre affiché |
| `default_status` | Statut initial d'une nouvelle candidature |
| `scraper.timeout_seconds` / `scraper.user_agent` | Téléchargement des annonces |
| `scraper.browser_fallback` / `scraper.browser_timeout_seconds` | Repli sur un navigateur headless |
| `host` / `port` / `debug` | Serveur |

Le dossier de données est surchargé par la variable d'environnement
`ASSISTANT_EMPLOI_DATA_DIR` (utilisée par Docker et les tests).

## Docker

```bash
docker build -t assistant-emploi .
docker run -p 8050:8050 -v "$(pwd)/data":/data assistant-emploi
```

La base vide est créée au premier démarrage ; le volume `/data` assure la persistance
(base SQLite, CV, copies d'annonces, exports). Un workflow GitHub Actions publie
également l'image sur le GitHub Container Registry (`ghcr.io/<utilisateur>/<dépôt>`).

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Structure

```
run.py                     Point d'entrée (serveur de développement)
config.json                Configuration
assistant_emploi/
  config.py                Chemins + chargement config
  models.py                Modèles SQLAlchemy
  database.py              Moteur, session, init / reset
  repository.py            Accès aux données (CRUD + recherche)
  scraper.py               Téléchargement des copies d'annonces
  exporter.py              Export ODS
  stats.py                 Figures Plotly des statistiques
  ods_import.py            Import depuis un tableur ODS
  manage.py                CLI de gestion de la base
  ui/                      Composants (thème, accueil, lettres, modales)
  callbacks/               Callbacks Dash
  app.py                   Application Dash + routes Flask
assets/style.css           Thème anthracite / ambre
tests/                     Tests unitaires (pytest)
Dockerfile                 Image de production (gunicorn)
data/                      Base SQLite, CV, annonces, exports (git-ignoré)
```

## Licence

Distribué sous licence [Apache 2.0](LICENSE).
