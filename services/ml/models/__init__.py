def __init__(self, model_path=None):
    """
    Initialise le détecteur
    
    Args:
        model_path: Chemin vers best.pt (optionnel)
    """
    # Forcer CPU
    torch.set_num_threads(1)
    
    # Chemin par défaut
    if model_path is None:
        model_path = os.path.join(
            os.path.dirname(__file__),
            'models',
            'best.pt'
        )
    
    # Vérifier que le modèle existe
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Modèle introuvable : {model_path}\n"
            f"Place ton fichier best.pt dans services/ml/models/"
        )
    
    print(f"🔄 Chargement du modèle depuis {model_path}...")
    
    # FIX PYTORCH 2.6+ : Patcher torch.load temporairement
    original_torch_load = torch.load
    
    def patched_torch_load(*args, **kwargs):
        # Forcer weights_only=False pour contourner la sécurité PyTorch 2.6+
        kwargs['weights_only'] = False
        return original_torch_load(*args, **kwargs)
    
    # Appliquer le patch
    torch.load = patched_torch_load
    
    try:
        # Charger le modèle avec le patch actif
        self.model = YOLO(model_path)
    finally:
        # Restaurer torch.load original
        torch.load = original_torch_load
    
    # Forcer CPU
    self.device = 'cpu'
    self.model.to(self.device)
    
    print(f"✅ Modèle chargé sur {self.device}")
    
    # Noms des classes
    self.class_names = {
        0: 'Bosse',
        1: 'Rayure',
        2: 'Fissure',
        3: 'Verre brisé',
        4: 'Lampe cassée',
        5: 'Pneu crevé'
    }
    
    # Couleurs pour les classes
    self.colors = {
        0: (255, 165, 0),   # Orange
        1: (135, 206, 235), # Bleu clair
        2: (255, 0, 0),     # Rouge
        3: (128, 0, 128),   # Violet
        4: (255, 255, 0),   # Jaune
        5: (220, 20, 60)    # Crimson
    }