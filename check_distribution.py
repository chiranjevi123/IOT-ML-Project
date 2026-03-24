import pandas as pd
# Load your dataset (change filename if needed)
df = pd.read_csv("soil_dataa.csv")

# Check class distribution
print("Class Distribution:\n")
print(df['plant_health'].value_counts())