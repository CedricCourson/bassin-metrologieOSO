Focntionnement

# Lancement du programme
-----------------------

Pour lancer le programme de régulation de température du bassin  : 
1- Se connecter au Raspberry en SSH
2- Se rendre dans le dossier /home/python/bassin-metreologie/cedtest en ligne de commande
3- lancer le script python AssTemp_v6.py

# Configuration
---------------- 
le fichier palier.txt contient les infos de configuration des paliers. il doit avoir la syntaxe suivante : 
boucle - 2
10 - 1800
15 - 1800
20 - 1800
25 - 1800
30 - 1800
il réalise deux fois les cycles de paliers. les paliers s'échelonne de 10 à 30°C sur cette example et chaque palier dure 1800s

Si on indique 0 à boucle, alors il va boucler à l'infinie. 

On peut configurer le script pour envoyer les données en temps r�el sur thingspeak. Dans le cas le script devra etre lanc� comme suit : 
>> python AssTemp_v6.py --thingspeak yes


# les données 
-------------
Les données sont systématiquement enregistrer sur le fichier CSV qui s'appelle data_bassin.csv

on peut aussi visualiser et télecharger les données sur thingspeak à l'adresse : https://thingspeak.mathworks.com/channels/2229533