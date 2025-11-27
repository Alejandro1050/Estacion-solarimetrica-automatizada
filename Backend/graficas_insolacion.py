import polars as pl
import plotly.express as px
from datetime import datetime
import argparse

date = datetime.now().strftime("%d-%m-%Y")

ap = argparse.ArgumentParser()
ap.add_argument("--file", required=False, help="Archivo ETL a procesar", default=f"/home/barba_negra/data/{date}_etl_data.csv")
args = vars(ap.parse_args())

# Leer el archivo CSV ya corregido
print("Leyendo archivo ETL...")
df = pl.read_csv(args["file"], infer_schema_length=10000)

print("\nPrimeras filas:")
print(df.head())

# Convertir la columna Datetime a tipo datetime y luego extraer el tiempo
df = df.with_columns([
    pl.col("Datetime")
    .str.strptime(pl.Datetime, "%d-%m-%Y %H:%M:%S")
    .alias("Datetime")
])

df = df.with_columns([
    pl.col("Datetime").dt.time().alias("Time")
])

# Obtenemos dataframes de cada radiación
df_ghi = df.select(["Time", "GHI(W/m²)"]).sort("Time")
df_dni = df.select(["Time", "DNI(W/m²)"]).sort("Time")
df_dhi = df.select(["Time", "DHI(W/m²)"]).sort("Time")

#print("\nPromedios por hora:")
#print("GHI:", df_ghi)
#print("DNI:", df_dni)
#print("DHI:", df_dhi)

# Convertir a Pandas para Plotly 
df_ghi_pd = df_ghi.to_pandas()
df_dni_pd = df_dni.to_pandas()
df_dhi_pd = df_dhi.to_pandas()

# Generar gráficas HTML (Plotly)
fig_ghi = px.line(df_ghi_pd, x="Time", y="GHI(W/m²)", markers=True, 
                  title=f"GHI {date}")
fig_dni = px.line(df_dni_pd, x="Time", y="DNI(W/m²)", markers=True, 
                  title=f"DNI {date}")
fig_dhi = px.line(df_dhi_pd, x="Time", y="DHI(W/m²)", markers=True, 
                  title=f"DHI {date}")

# Actualizar layouts
fig_ghi.update_layout(xaxis_title="Hora del día", yaxis_title="GHI (W/m²)")
fig_dni.update_layout(xaxis_title="Hora del día", yaxis_title="DNI (W/m²)")
fig_dhi.update_layout(xaxis_title="Hora del día", yaxis_title="DHI (W/m²)")

# Crear directorio para las gráficas si no existe
import os
output_dir = "/home/barba_negra/data/graficas"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Guardar gráficas como PNG
fig_ghi.write_image(f"{output_dir}/GHI_{date}.png")
fig_dni.write_image(f"{output_dir}/DNI_{date}.png")
fig_dhi.write_image(f"{output_dir}/DHI_{date}.png")

print(f"\nGráficas guardadas en el directorio '{output_dir}':")
print(f"- GHI_{date}.png")
print(f"- DNI_{date}.png")
print(f"- DHI_{date}.png")

# Mostrar gráficas interactivas (opcional)
#fig_ghi.show()
#fig_dni.show()
#fig_dhi.show()

