# 🚀 Déploiement PLUMATOTM sur Render

Guide complet pour déployer l'API PLUMATOTM sur Render.

## 📋 Prérequis

- Compte Render (gratuit)
- Repository GitHub avec votre code
- Python 3.9+

## 🔧 Étapes de déploiement

### 1. **Préparer votre repository**

Assurez-vous que votre repository contient :

```
plumatotm/
├── plumatotm_api.py          # API FastAPI
├── plumatotm_core.py         # Moteur d'analyse
├── plumatotm_radar.py        # Générateur de graphiques
├── requirements_api.txt      # Dépendances Python
├── render.yaml              # Configuration Render
├── plumatotm_raw_scores.json
├── plumatotm_planets_weights.csv
├── plumatotm_planets_multiplier.csv
└── README.md
```

### 2. **Créer un compte Render**

1. Allez sur [render.com](https://render.com)
2. Créez un compte gratuit
3. Connectez votre compte GitHub

### 3. **Déployer l'API**

#### Option A : Déploiement automatique avec render.yaml

1. **Poussez votre code sur GitHub**
2. **Dans Render Dashboard :**
   - Cliquez "New +"
   - Sélectionnez "Blueprint"
   - Connectez votre repository
   - Render détectera automatiquement le `render.yaml`

#### Option B : Déploiement manuel

1. **Dans Render Dashboard :**
   - Cliquez "New +"
   - Sélectionnez "Web Service"
   - Connectez votre repository GitHub

2. **Configuration :**
   ```
   Name: plumatotm-api
   Environment: Python 3
   Build Command: pip install -r requirements_api.txt
   Start Command: python plumatotm_api.py
   ```

3. **Variables d'environnement :**
   ```
   PORT: 8000
   PYTHON_VERSION: 3.9
   ```

### 4. **Vérifier le déploiement**

Une fois déployé, votre API sera disponible à :
```
https://votre-app-name.onrender.com
```

## 🧪 Tests de l'API

### Test de santé
```bash
curl https://votre-app-name.onrender.com/health
```

### Test d'analyse
```bash
curl -X POST "https://votre-app-name.onrender.com/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "1990-05-15",
    "time": "14:30",
    "lat": 48.8566,
    "lon": 2.3522,
    "name": "Test User"
  }'
```

## 🔗 Intégration Shopify

Dans votre formulaire Shopify, configurez l'URL :

```liquid
{% schema %}
{
  "settings": [
    {
      "type": "text",
      "id": "api_url",
      "label": "URL de l'API PLUMATOTM",
      "default": "https://votre-app-name.onrender.com/analyze"
    }
  ]
}
{% endschema %}
```

## ⚠️ Points importants

### 1. **Limitations Render Free**
- 750 heures/mois
- 15 minutes d'inactivité = arrêt automatique
- Redémarrage automatique au premier appel

### 2. **Performance**
- Premier appel après inactivité : 30-60 secondes
- Appels suivants : 2-5 secondes

### 3. **Stockage**
- Les fichiers générés (outputs/) sont temporaires
- Pas de persistance entre les redémarrages

## 🔧 Optimisations

### 1. **Pour la production**
- Passez au plan payant pour éviter les arrêts
- Configurez des variables d'environnement pour les secrets

### 2. **Monitoring**
- Utilisez `/health` pour vérifier l'état
- Surveillez les logs dans le dashboard Render

### 3. **Sécurité**
- Limitez les origines CORS en production
- Ajoutez une authentification si nécessaire

## 🐛 Dépannage

### Erreur de build
```bash
# Vérifiez les logs dans Render Dashboard
# Assurez-vous que requirements_api.txt est correct
```

### Erreur 500
```bash
# Vérifiez que tous les fichiers de données sont présents
# Testez localement d'abord
```

### Timeout
```bash
# L'analyse peut prendre du temps
# Augmentez le timeout dans votre frontend
```

## 📞 Support

- **Logs Render :** Dashboard → Votre app → Logs
- **Documentation API :** `https://votre-app-name.onrender.com/docs`
- **Health Check :** `https://votre-app-name.onrender.com/health`

---

🎉 Votre API PLUMATOTM est maintenant prête à être utilisée avec Shopify !
