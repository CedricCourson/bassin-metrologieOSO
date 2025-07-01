Focntionnement

# Lancement du programme
-----------------------

Pour lancer le programme de r�gulation de temp�rature du bassin  : 
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
il r�alise deux fois les cycles de paliers. les paliers s'�chelonne de 10 � 30�C sur cette example et chaque palier dure 1800s

Si on indique 0 � boucle, alors il va boucler � l'infinie. 

On peut configurer le script pour envoyer les donn�es en temps r�el sur thingspeak. Dans le cas le script devra etre lanc� comme suit : 
>> python AssTemp_v6.py --thingspeak yes


# les donn�es 
-------------
Les donn�es sont syst�matiquement enregistrer sur le fichier CSV qui s'appelle data_bassin.csv

on peut aussi visualiser et t�lecharger les donn�es sur thingspeak � l'adresse : https://thingspeak.mathworks.com/channels/2229533