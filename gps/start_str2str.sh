#!/bin/bash

# Datei mit Umgebungsvariablen einlesen
ENV_FILE=".env"

# Überprüfen, ob die Datei existiert
if [ -f "$ENV_FILE" ]; then
    echo "Lese Umgebungsvariablen aus $ENV_FILE..."
    source "$ENV_FILE"
else
    echo "Die Datei $ENV_FILE existiert nicht."
    exit 1
fi

# Befehl ausführen, wenn Umgebungsvariable gesetzt ist
if [ -n "$STR2STR_TCPSVR" ]; then
    echo "Starte str2str mit TCP-Server..."
    str2str -in "$STR2STR_SERIAL" -b 1 -out "$STR2STR_NTRIP" -out "$STR2STR_TCPSVR"
else
    echo "Die Umgebungsvariable STR2STR_TCPSVR ist nicht gesetzt."
    exit 1
fi