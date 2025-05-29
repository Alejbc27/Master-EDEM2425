#!/bin/sh
set -e  # Detener el script si algún comando falla

echo "Ejecutando loadDistrict.py..."
python Functions/ManageData/loadDistrict.py

echo "Ejecutando loadEducation.py..."
python Functions/ManageData/loadEducation.py

echo "Ejecutando loadGreenArea.py..."
python Functions/ManageData/loadGreenArea.py

echo "Ejecutando loadHospitals.py..."
python Functions/ManageData/loadHospitals.py

echo "Ejecutando loadPostalCode.py..."
python Functions/ManageData/loadPostalCode.py

echo "Ejecutando loadRentPrice.py..."
python Functions/ManageData/loadRentPrice.py

echo "Ejecutando loadSalesPrice.py..."
python Functions/ManageData/loadSalesPrice.py

echo "Ejecutando loadTransport.py..."
python Functions/ManageData/loadTransport.py

echo "Iniciando Streamlit..."
exec streamlit run Functions/main.py