"""Client CLF-Expert — SQUELETTE VIDE (préparation passive, ne rien appeler).

Rôle FUTUR de ce module :
    Encapsuler TOUS les appels vers l'API du système expert externe CLF-Expert
    (source de vérité juridique sur la Charte de la langue française), une fois
    que cette API existera. Le reste de l'application NE DOIT JAMAIS dépendre
    directement de la structure de l'API externe : toute interaction passera par
    ce module (récupération d'un objet juridique, de sa version, de sa citation,
    reconstruction de l'état du droit à une date donnée, etc.).

État actuel : CLF-Expert n'expose aucune API d'interrogation. On n'implémente
donc RIEN ici — pas de client HTTP, pas d'appel réseau, pas d'authentification.
Les champs passifs `external_*` / `reference_date` / `retrieved_at` sur les
thèmes et mesures sont prévus pour accueillir ces références plus tard, sans
migration de données.

NE PAS ajouter d'appel réseau réel tant que l'API CLF-Expert n'est pas disponible.
"""
