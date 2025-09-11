# dashboardus/appus.py

import dash

def create_app(df, user_id_to_name_map, role_colors_map):
    """
    Crée et configure l'application Dash.
    """
    # Utilisation d'un thème Bootstrap 5 moderne (Litera) et de Font Awesome pour les icônes
    EXTERNAL_STYLESHEETS = [
        "https://bootswatch.com/5/litera/bootstrap.min.css",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css"
    ]

    # Dash charge automatiquement les feuilles de style dans le dossier 'assets'
    app = dash.Dash(
        __name__,
        title="Statistiques Discord",
        external_stylesheets=EXTERNAL_STYLESHEETS
    )

    # Importation et configuration de la mise en page
    from .layoutus import create_layout
    app.layout = create_layout(df)

    # Enregistrement des fonctions de callback
    from .callbackus import register_callbacks
    register_callbacks(app, df, user_id_to_name_map, role_colors_map)

    return app
