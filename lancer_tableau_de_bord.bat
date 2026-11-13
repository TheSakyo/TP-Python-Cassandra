rem Masque les commandes pour que la fenêtre du lanceur reste lisible.
@echo off
rem Place le dossier courant à la racine du projet, quel que soit le point de lancement.
cd /d "%~dp0"
rem Vérifie que l'environnement virtuel du projet existe.
if not exist ".venv\Scripts\python.exe" (
    rem Explique comment corriger l'absence de l'environnement Python.
    echo Environnement Python introuvable. Cree d'abord le venv et installe requirements.txt.
    rem Attend une touche pour laisser le message visible.
    pause
    rem Termine le script avec un code d'erreur.
    exit /b 1
)
rem Lance l'application web avec les dépendances du projet.
.venv\Scripts\python.exe -m src.web_ui
rem Attend une touche après l'arrêt du serveur web.
pause
