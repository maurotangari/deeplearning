# -*- coding: utf-8 -*-
"""Hybrid (Mixture Model).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1cMuuL5kFVF6AL9Gse8n8wFyDrZaMvZj2
"""

from os import name
import pandas as pd
import datetime
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import layers
from copy import deepcopy
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.optimizers.schedules import ExponentialDecay
import tensorflow as tf
from tensorflow.keras.layers import Input, Activation, Attention, Concatenate, Conv1D, Dense, Dropout, BatchNormalization, Layer, LayerNormalization, MultiHeadAttention, Add, GlobalAveragePooling1D, Bidirectional, LSTM
from sklearn.metrics import mean_squared_error, r2_score
from tensorflow.keras.utils import plot_model

#--------------------DATA PRE-PROCESS------------------------------------------------
# Definizione della funzione per convertire una stringa in un oggetto datetime
def str_to_datetime(s):
    split = s.split('-')
    year, month, day = int(split[0]), int(split[1]), int(split[2])
    return datetime.datetime(year=year, month=month, day=day)

# Caricamento dei dati dai file CSV
df = pd.read_csv('AAPL.csv')
#df = pd.read_csv('AMZN.csv')
#df = pd.read_csv('GOOG.csv')
#df = pd.read_csv('MSFT.csv')

# Selezione delle colonne di interesse (Date, Close, Open, High, Low, Volume)
df = df[['Date', 'Close', 'Open', 'High', 'Low', 'Volume']]

# Conversione delle date da stringa a oggetti datetime
df['Date'] = df['Date'].apply(str_to_datetime)
df.index = df.pop('Date')

# Rimozione delle righe con dati mancanti o nulli
df.dropna(inplace=True)

# Normalizzazione dei dati utilizzando la tecnica Min-Max
scaler = MinMaxScaler()
df[['Close', 'Open', 'High', 'Low', 'Volume']] = scaler.fit_transform(df[['Close', 'Open', 'High', 'Low', 'Volume']])

# Creazione di input (X) e target (y) dai dati
X = df[['Close', 'Open', 'High', 'Low', 'Volume']].values
y = df[['Close', 'Open', 'High', 'Low', 'Volume']].values  # Target multi-output

# Calcolo delle dimensioni dei set
train_size = int(len(X) * 0.8)
val_size = int(train_size * 0.2)  # 20% del training set

# Divisione dei dati in set di addestramento, validazione e test
X_train, y_train = X[:train_size - val_size], y[:train_size - val_size]
X_val, y_val = X[train_size - val_size:train_size], y[train_size - val_size:train_size]
X_test, y_test = X[train_size:], y[train_size:]

# Aggiungi una dimensione temporale fittizia così X_train_3d, X_val_3d e X_test_3d hanno la forma (1006, 1, 5)
X_train_3d = X_train[:, np.newaxis, :]
X_val_3d = X_val[:, np.newaxis, :]
X_test_3d = X_test[:, np.newaxis, :]

# Aggiungi una dimensione temporale anche per i target
y_train_3d = y_train[:, np.newaxis, :]
y_val_3d = y_val[:, np.newaxis, :]
y_test_3d = y_test[:, np.newaxis, :]



#-----------------------------------------BI-LSTM--------------------------------------------------------------------------------------
# Definizione dello strato di Self-Attention
class SelfAttention(Layer):
    def __init__(self, num_heads, head_dim, **kwargs):
        super(SelfAttention, self).__init__(**kwargs)
        self.num_heads = num_heads
        self.head_dim = head_dim

    def build(self, input_shape):
        self.W_q = self.add_weight("W_q", shape=(input_shape[-1], self.num_heads * self.head_dim))
        self.W_k = self.add_weight("W_k", shape=(input_shape[-1], self.num_heads * self.head_dim))
        self.W_v = self.add_weight("W_v", shape=(input_shape[-1], self.num_heads * self.head_dim))

    def call(self, inputs):
        q = tf.matmul(inputs, self.W_q)
        k = tf.matmul(inputs, self.W_k)
        v = tf.matmul(inputs, self.W_v)

        q = tf.reshape(q, (-1, tf.shape(q)[1], self.num_heads, self.head_dim))
        k = tf.reshape(k, (-1, tf.shape(k)[1], self.num_heads, self.head_dim))
        v = tf.reshape(v, (-1, tf.shape(v)[1], self.num_heads, self.head_dim))

        attention_scores = tf.matmul(q, k, transpose_b=True)
        attention_scores = tf.nn.softmax(attention_scores, axis=-1)

        output = tf.matmul(attention_scores, v)
        output = tf.reshape(output, (-1, tf.shape(output)[1], self.num_heads * self.head_dim))

        return output

# Dimensioni dei dati
num_features = 5  # Numero di features nel dataset
num_heads = 8     # Numero di teste per l'attenzione multi-head
head_dim = 64     # Dimensione di ogni testa di attenzione

# Creazione del modello Sequential
bi_lstm_attention_model = Sequential(name='BiLSTM')

# Aggiunta degli strati al modello
bi_lstm_attention_model.add(Input(shape=(None, 5)))
bi_lstm_attention_model.add(Activation('relu'))
bi_lstm_attention_model.add(Bidirectional(LSTM(512, return_sequences=True)))
bi_lstm_attention_model.add(Dropout(0.2))
bi_lstm_attention_model.add(Activation('relu'))
bi_lstm_attention_model.add(Bidirectional(LSTM(256, return_sequences=True)))
bi_lstm_attention_model.add(Dropout(0.2))
bi_lstm_attention_model.add(SelfAttention(num_heads=num_heads, head_dim=head_dim))
bi_lstm_attention_model.add(Dense(512, activation='relu'))
bi_lstm_attention_model.add(Dense(256, activation='relu'))
bi_lstm_attention_model.add(Dense(128, activation='relu'))
bi_lstm_attention_model.add(Dense(64, activation='relu'))
bi_lstm_attention_model.add(Dense(32, activation='relu', kernel_regularizer=l2(0.005)))
bi_lstm_attention_model.add(Dense(5))

# Compilazione del modello
bi_lstm_attention_model.compile(loss='mse', optimizer=Adam(learning_rate=0.000015), metrics=['mean_absolute_error'])

# Stampa un riassunto del modello
bi_lstm_attention_model.summary()

# Aggiunta di un callback per ridurre il tasso di apprendimento su plateau
lr_scheduler = ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=10, verbose=1, min_lr=1e-6)
callbacks = [lr_scheduler]

# Esempio di utilizzo nei fit e predict del modello
history = bi_lstm_attention_model.fit(X_train_3d, y_train_3d, validation_data=(X_val_3d, y_val_3d),
                                      epochs=150,
                                      batch_size=64,
                                      callbacks=callbacks,
                                      verbose=1)
predictions_val = bi_lstm_attention_model.predict(X_val_3d)
predictions_test = bi_lstm_attention_model.predict(X_test_3d)


# Valuta il modello sull'insieme di test
test_loss, test_mae = bi_lstm_attention_model.evaluate(X_test_3d, y_test_3d, verbose=0)

# Riduci le dimensioni di y_test_3d a (1006, 5)
y_test_2d = y_test_3d.reshape(-1, 5)

# Rimuovi il terzo asse dalle previsioni
predictions_test_squeezed = np.squeeze(predictions_test)

# Calcola il RMSE
rmse = np.sqrt(mean_squared_error(y_test_2d, predictions_test_squeezed))

# Calcola il R-squared (R²)
r2 = r2_score(y_test_2d, predictions_test_squeezed)

print(f'Test Loss: {test_loss}')
print(f'Test Mean Absolute Error (MAE): {test_mae}')
print(f'Test Root Mean Squared Error (RMSE): {rmse}')
print(f'Test R-squared (R²): {r2}')



# Creazione dei grafici delle learning curve
plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.title('Training and Validation Loss')

plt.subplot(1, 2, 2)
plt.plot(history.history['mean_absolute_error'], label='Training MAE')
plt.plot(history.history['val_mean_absolute_error'], label='Validation MAE')
plt.xlabel('Epoch')
plt.ylabel('Mean Absolute Error')
plt.legend()
plt.title('Training and Validation Mean Absolute Error')

plt.tight_layout()
plt.show()

# Trova l'indice dell'epoca con la minima val_loss e loss
best_epoch_val = np.argmin(history.history['val_loss'])
best_epoch = np.argmin(history.history['loss'])
# Trova il valore minimo della val_loss e loss
best_val_loss = history.history['val_loss'][best_epoch_val]
best_loss = history.history['loss'][best_epoch]
# Stampa il risultato
print(f'Best Validation Loss: {best_val_loss:.4f} at epoch {best_epoch_val + 1}')
print(f'Best Training Loss: {best_loss:.4f} at epoch {best_epoch + 1}')


feature_names = ['Close', 'Open', 'High', 'Low']  # Escludi la feature 'Volume'

plt.figure(figsize=(12, 24))  # Imposta la dimensione complessiva del grafico

total_train_samples = len(y_train)
total_val_samples = len(y_val)
total_test_samples = len(y_test)


# Estrai le date dei dati di addestramento e validazione
dates_train = df.index[:total_train_samples]
dates_val = df.index[total_train_samples:total_train_samples + total_val_samples]
dates_test = df.index[total_train_samples + total_val_samples:]

# Creazione dei grafici delle previsioni per ciascuna feature
for feature_index, feature_name in enumerate(feature_names):
    plt.figure(figsize=(12, 4))

    # Estrai i dati reali e le previsioni per la caratteristica specifica
    y_train_feature = y_train_3d[:, 0, feature_index]
    y_val_feature = y_val_3d[:, 0, feature_index]
    predictions_val_feature = predictions_val[:, 0, feature_index]
    y_test_feature = y_test_3d[:, 0, feature_index]
    predictions_test_feature = predictions_test[:, 0, feature_index]

    plt.plot(dates_train, y_train_feature, color='blue', label=f'Dati Reali di Training {feature_name}', linewidth=2.5)
    plt.plot(dates_val, y_val_feature, color='orange', label=f'Dati Reali di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_val, predictions_val_feature, color='red', label=f'Previsioni di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_test, y_test_feature, color='yellow', label=f'Dati Reali di Test {feature_name}', linewidth=2.5)
    plt.plot(dates_test, predictions_test_feature, color='green', label=f'Previsioni di Test {feature_name}', linewidth=2.5)

    plt.xlabel('Data')
    plt.ylabel('Valore')
    plt.title(f'Confronto tra Previsioni e Dati Reali di {feature_name}')
    plt.legend()
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()

# Crea un DataFrame da y_val con nomi di colonne appropriati
y_val_df = pd.DataFrame(y_val_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_val_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_val_df = pd.DataFrame(predictions_val[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_val_df)
# Crea un DataFrame da y_val con nomi di colonne appropriati
y_test_df = pd.DataFrame(y_test_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_test_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_test_df = pd.DataFrame(predictions_test[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_test_df)
# Unisci i due DataFrame in uno solo
combined_df = pd.concat([y_val_df, predictions_val_df], axis=1)

# Stampa il DataFrame risultante
#print(combined_df)

#--------------------stampare un grafico del modello-------------------------------------------------
plot_model(bi_lstm_attention_model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)

# --------------------------TRANSFORMER-------------------------------------------------------------------------------------------------
# Dimensioni dei dati
num_features = 5  # Numero di features nel dataset
num_heads = 8     # Numero di teste per l'attenzione multi-head
head_dim = 64     # Dimensione di ogni testa di attenzione

# Creazione del modello Sequential
transformer_model = Sequential(name='Transformer')

# Aggiunta degli strati al modello
input_layer = Input(shape=(None, num_features))  # Adatta la forma all'intero dataset

# Primo encoder
encoder_1 = SelfAttention(num_heads=num_heads, head_dim=head_dim)(input_layer)
encoder_1 = Dense(128, activation='relu')(encoder_1)
encoder_1 = Dense(128, activation='relu')(encoder_1)

# Secondo encoder
encoder_2 = SelfAttention(num_heads=num_heads, head_dim=head_dim)(encoder_1)
encoder_2 = Dense(64, activation='relu')(encoder_2)
encoder_2 = Dense(64, activation='relu')(encoder_2)

# Concatena l'output dei due encoder
concatenated_output = Concatenate()([encoder_1, encoder_2])

# Output layer
output_layer = Dense(num_features)(concatenated_output)

# Aggiungi l'output layer al modello
transformer_model = tf.keras.Model(inputs=input_layer, outputs=output_layer, name='Transformer')


# Creazione del modello con self-attention e più strati
transformer_model.compile(loss='mse',
              optimizer=Adam(learning_rate=0.00001),
              metrics=['mean_absolute_error'])

# Stampa un riassunto del modello
transformer_model.summary()

# Aggiunta di un callback per ridurre il tasso di apprendimento su plateau
lr_scheduler = ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=10, verbose=1, min_lr=1e-6)
callbacks = [lr_scheduler]

history = transformer_model.fit(X_train_3d, y_train_3d, validation_data=(X_val_3d, y_val_3d),
                                      epochs=150,
                                      batch_size=64,
                                      callbacks=callbacks,
                                      verbose=1)


# Creazione delle previsioni sui dati di validazione e test
predictions_val = transformer_model.predict(X_val_3d)
predictions_test = transformer_model.predict(X_test_3d)

# Valuta il modello sull'insieme di test
test_loss, test_mae = transformer_model.evaluate(X_test_3d, y_test_3d, verbose=0)

# Riduci le dimensioni di y_test_3d a (1006, 5)
y_test_2d = y_test_3d.reshape(-1, 5)

# Rimuovi il terzo asse dalle previsioni
predictions_test_squeezed = np.squeeze(predictions_test)

# Calcola il RMSE
rmse = np.sqrt(mean_squared_error(y_test_2d, predictions_test_squeezed))

# Calcola il R-squared (R²)
r2 = r2_score(y_test_2d, predictions_test_squeezed)

print(f'Test Loss: {test_loss}')
print(f'Test Mean Absolute Error (MAE): {test_mae}')
print(f'Test Root Mean Squared Error (RMSE): {rmse}')
print(f'Test R-squared (R²): {r2}')


# Creazione dei grafici delle learning curve
plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.title('Training and Validation Loss')

plt.subplot(1, 2, 2)
plt.plot(history.history['mean_absolute_error'], label='Training MAE')
plt.plot(history.history['val_mean_absolute_error'], label='Validation MAE')
plt.xlabel('Epoch')
plt.ylabel('Mean Absolute Error')
plt.legend()
plt.title('Training and Validation Mean Absolute Error')

plt.tight_layout()
plt.show()

# Trova l'indice dell'epoca con la minima val_loss e loss
best_epoch_val = np.argmin(history.history['val_loss'])
best_epoch = np.argmin(history.history['loss'])
# Trova il valore minimo della val_loss e loss
best_val_loss = history.history['val_loss'][best_epoch_val]
best_loss = history.history['loss'][best_epoch]
# Stampa il risultato
print(f'Best Validation Loss: {best_val_loss:.4f} at epoch {best_epoch_val + 1}')
print(f'Best Training Loss: {best_loss:.4f} at epoch {best_epoch + 1}')


feature_names = ['Close', 'Open', 'High', 'Low']  # Escludi la feature 'Volume'

plt.figure(figsize=(12, 24))  # Imposta la dimensione complessiva del grafico

total_train_samples = len(y_train)
total_val_samples = len(y_val)
total_test_samples = len(y_test)


# Estrai le date dei dati di addestramento e validazione
dates_train = df.index[:total_train_samples]
dates_val = df.index[total_train_samples:total_train_samples + total_val_samples]
dates_test = df.index[total_train_samples + total_val_samples:]

# Creazione dei grafici delle previsioni per ciascuna feature
for feature_index, feature_name in enumerate(feature_names):
    plt.figure(figsize=(12, 4))

    # Estrai i dati reali e le previsioni per la caratteristica specifica
    y_train_feature = y_train_3d[:, 0, feature_index]
    y_val_feature = y_val_3d[:, 0, feature_index]
    predictions_val_feature = predictions_val[:, 0, feature_index]
    y_test_feature = y_test_3d[:, 0, feature_index]
    predictions_test_feature = predictions_test[:, 0, feature_index]

    plt.plot(dates_train, y_train_feature, color='blue', label=f'Dati Reali di Training {feature_name}', linewidth=2.5)
    plt.plot(dates_val, y_val_feature, color='orange', label=f'Dati Reali di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_val, predictions_val_feature, color='red', label=f'Previsioni di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_test, y_test_feature, color='yellow', label=f'Dati Reali di Test {feature_name}', linewidth=2.5)
    plt.plot(dates_test, predictions_test_feature, color='green', label=f'Previsioni di Test {feature_name}', linewidth=2.5)

    plt.xlabel('Data')
    plt.ylabel('Valore')
    plt.title(f'Confronto tra Previsioni e Dati Reali di {feature_name}')
    plt.legend()
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()

# Crea un DataFrame da y_val con nomi di colonne appropriati
y_val_df = pd.DataFrame(y_val_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_val_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_val_df = pd.DataFrame(predictions_val[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_val_df)
# Crea un DataFrame da y_val con nomi di colonne appropriati
y_test_df = pd.DataFrame(y_test_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_test_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_test_df = pd.DataFrame(predictions_test[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_test_df)
# Unisci i due DataFrame in uno solo
combined_df = pd.concat([y_val_df, predictions_val_df], axis=1)

# Stampa il DataFrame risultante
#print(combined_df)

#--------------------stampare un grafico del modello-------------------------------------------------
plot_model(transformer_model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)


#-----------------------------------------------Hybrid Model-----------------------------------------------------------------------
from keras.layers import Average
num_features=5

# Creazione del modello ibrido
input_layer = Input(shape=(None, num_features))
bi_lstm_predictions = bi_lstm_attention_model(input_layer)
transformer_predictions = transformer_model(input_layer)
combined_predictions = Average()([bi_lstm_predictions, transformer_predictions])

hybrid_model = Model(inputs=input_layer, outputs=combined_predictions, name='HybridMixture')

# Compilazione del modello ibrido
hybrid_model.compile(loss='mse', optimizer=Adam(learning_rate=0.00001), metrics=['mean_absolute_error'])

# Stampa un riassunto del modello ibrido
hybrid_model.summary()

# Creazione delle previsioni sui dati di validazione e test
hybrid_predictions_val = hybrid_model.predict(X_val_3d)
hybrid_predictions_test = hybrid_model.predict(X_test_3d)

from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
# Riduci le dimensioni di y_test_3d a (1006, 5)
y_test_2d = y_test_3d.reshape(-1, 5)

# Rimuovi il terzo asse dalle previsioni
hybrid_predictions_test_squeezed = np.squeeze(hybrid_predictions_test)

# Calcola il RMSE
rmse = np.sqrt(mean_squared_error(y_test_2d, hybrid_predictions_test_squeezed))

# Calcola il R-squared (R²)
r2 = r2_score(y_test_2d, hybrid_predictions_test_squeezed)

# Calcola il MAE
mae = mean_absolute_error(y_test_2d, hybrid_predictions_test_squeezed)

print(f'RMSE Hybrid Model (mixture): {rmse}')
print(f'R-squared Hybrid Model (mixture): {r2}')
print(f'MAE Hybrid Model (mixture): {mae}')

feature_names = ['Close', 'Open', 'High', 'Low']  # Escludi la feature 'Volume'

plt.figure(figsize=(12, 24))  # Imposta la dimensione complessiva del grafico

total_train_samples = len(y_train)
total_val_samples = len(y_val)
total_test_samples = len(y_test)


# Estrai le date dei dati di addestramento e validazione
dates_train = df.index[:total_train_samples]
dates_val = df.index[total_train_samples:total_train_samples + total_val_samples]
dates_test = df.index[total_train_samples + total_val_samples:]

# Creazione dei grafici delle previsioni per ciascuna feature
for feature_index, feature_name in enumerate(feature_names):
    plt.figure(figsize=(12, 4))

    # Estrai i dati reali e le previsioni per la caratteristica specifica
    y_train_feature = y_train_3d[:, 0, feature_index]
    y_val_feature = y_val_3d[:, 0, feature_index]
    predictions_val_feature = predictions_val[:, 0, feature_index]
    y_test_feature = y_test_3d[:, 0, feature_index]
    predictions_test_feature = predictions_test[:, 0, feature_index]

    plt.plot(dates_train, y_train_feature, color='blue', label=f'Dati Reali di Training {feature_name}', linewidth=2.5)
    plt.plot(dates_val, y_val_feature, color='orange', label=f'Dati Reali di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_val, predictions_val_feature, color='red', label=f'Previsioni di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_test, y_test_feature, color='yellow', label=f'Dati Reali di Test {feature_name}', linewidth=2.5)
    plt.plot(dates_test, predictions_test_feature, color='green', label=f'Previsioni di Test {feature_name}', linewidth=2.5)

    plt.xlabel('Data')
    plt.ylabel('Valore')
    plt.title(f'Confronto tra Previsioni e Dati Reali di {feature_name}')
    plt.legend()
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()

# Crea un DataFrame da y_val con nomi di colonne appropriati
y_val_df = pd.DataFrame(y_val_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_val_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_val_df = pd.DataFrame(predictions_val[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_val_df)
# Crea un DataFrame da y_val con nomi di colonne appropriati
y_test_df = pd.DataFrame(y_test_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_test_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_test_df = pd.DataFrame(predictions_test[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_test_df)
# Unisci i due DataFrame in uno solo
combined_df = pd.concat([y_val_df, predictions_val_df], axis=1)

# Stampa il DataFrame risultante
#print(combined_df)

#--------------------stampare un grafico del modello-------------------------------------------------
plot_model(hybrid_model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)

import pandas as pd
import datetime
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, Activation, Attention, Concatenate, Conv1D, Dense, Dropout, BatchNormalization, Layer, LayerNormalization, MultiHeadAttention, Add, GlobalAveragePooling1D, Bidirectional, LSTM
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import layers
from copy import deepcopy
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.optimizers.schedules import ExponentialDecay
import tensorflow as tf
from tensorflow.keras.utils import plot_model


# Definizione della funzione per convertire una stringa in un oggetto datetime
def str_to_datetime(s):
    split = s.split('-')
    year, month, day = int(split[0]), int(split[1]), int(split[2])
    return datetime.datetime(year=year, month=month, day=day)

# Caricamento dei dati dai file CSV
#df = pd.read_csv('AAPL.csv')
#df = pd.read_csv('AMZN.csv')
df = pd.read_csv('GOOG.csv')
#df = pd.read_csv('MSFT.csv')

# Selezione delle colonne di interesse (Date, Close, Open, High, Low, Volume)
df = df[['Date', 'Close', 'Open', 'High', 'Low', 'Volume']]

# Conversione delle date da stringa a oggetti datetime
df['Date'] = df['Date'].apply(str_to_datetime)
df.index = df.pop('Date')

# Rimozione delle righe con dati mancanti o nulli
df.dropna(inplace=True)

# Normalizzazione dei dati utilizzando la tecnica Min-Max
scaler = MinMaxScaler()
df[['Close', 'Open', 'High', 'Low', 'Volume']] = scaler.fit_transform(df[['Close', 'Open', 'High', 'Low', 'Volume']])

# Creazione di input (X) e target (y) dai dati
X = df[['Close', 'Open', 'High', 'Low', 'Volume']].values
y = df[['Close', 'Open', 'High', 'Low', 'Volume']].values  # Target multi-output

# Calcolo delle dimensioni dei set
train_size = int(len(X) * 0.8)
val_size = int(train_size * 0.2)  # 20% del training set

# Divisione dei dati in set di addestramento, validazione e test
X_train, y_train = X[:train_size - val_size], y[:train_size - val_size]
X_val, y_val = X[train_size - val_size:train_size], y[train_size - val_size:train_size]
X_test, y_test = X[train_size:], y[train_size:]

# Aggiungi una dimensione temporale fittizia così X_train_3d, X_val_3d e X_test_3d hanno la forma (1006, 1, 5)
X_train_3d = X_train[:, np.newaxis, :]
X_val_3d = X_val[:, np.newaxis, :]
X_test_3d = X_test[:, np.newaxis, :]

# Aggiungi una dimensione temporale anche per i target
y_train_3d = y_train[:, np.newaxis, :]
y_val_3d = y_val[:, np.newaxis, :]
y_test_3d = y_test[:, np.newaxis, :]

# Definizione dello strato di Self-Attention
class SelfAttention(Layer):
    def __init__(self, num_heads, head_dim, **kwargs):
        super(SelfAttention, self).__init__(**kwargs)
        self.num_heads = num_heads
        self.head_dim = head_dim

    def build(self, input_shape):
        self.W_q = self.add_weight("W_q", shape=(input_shape[-1], self.num_heads * self.head_dim))
        self.W_k = self.add_weight("W_k", shape=(input_shape[-1], self.num_heads * self.head_dim))
        self.W_v = self.add_weight("W_v", shape=(input_shape[-1], self.num_heads * self.head_dim))

    def call(self, inputs):
        q = tf.matmul(inputs, self.W_q)
        k = tf.matmul(inputs, self.W_k)
        v = tf.matmul(inputs, self.W_v)

        q = tf.reshape(q, (-1, tf.shape(q)[1], self.num_heads, self.head_dim))
        k = tf.reshape(k, (-1, tf.shape(k)[1], self.num_heads, self.head_dim))
        v = tf.reshape(v, (-1, tf.shape(v)[1], self.num_heads, self.head_dim))

        attention_scores = tf.matmul(q, k, transpose_b=True)
        attention_scores = tf.nn.softmax(attention_scores, axis=-1)

        output = tf.matmul(attention_scores, v)
        output = tf.reshape(output, (-1, tf.shape(output)[1], self.num_heads * self.head_dim))

        return output

# Dimensioni dei dati
num_features = 5  # Numero di features nel dataset
num_heads = 8     # Numero di teste per l'attenzione multi-head
head_dim = 64     # Dimensione di ogni testa di attenzione

from tensorflow.keras.layers import Multiply, Add

# Definisci i modelli Bi-LSTM e Transformer separatamente
# Creazione del modello Sequential
bi_lstm_attention_model = Sequential(name="bilstm_model")

# Aggiunta degli strati al modello
bi_lstm_attention_model.add(Input(shape=(None, 5)))
bi_lstm_attention_model.add(Activation('relu'))
bi_lstm_attention_model.add(Bidirectional(LSTM(512, return_sequences=True)))
bi_lstm_attention_model.add(Dropout(0.2))
bi_lstm_attention_model.add(Activation('relu'))
bi_lstm_attention_model.add(Bidirectional(LSTM(256, return_sequences=True)))
bi_lstm_attention_model.add(Dropout(0.2))
bi_lstm_attention_model.add(SelfAttention(num_heads=num_heads, head_dim=head_dim))
bi_lstm_attention_model.add(Dense(512, activation='relu'))
bi_lstm_attention_model.add(Dense(256, activation='relu'))
bi_lstm_attention_model.add(Dense(128, activation='relu'))
bi_lstm_attention_model.add(Dense(64, activation='relu'))
bi_lstm_attention_model.add(Dense(32, activation='relu', kernel_regularizer=l2(0.005)))
bi_lstm_attention_model.add(Dense(5))

# Compilazione del modello
bi_lstm_attention_model.compile(loss='mse', optimizer=Adam(learning_rate=0.000015), metrics=['mean_absolute_error'])

# Creazione del modello Sequential
transformer_model = Sequential(name="transformer_model")

# Aggiunta degli strati al modello
input_layer = Input(shape=(None, num_features))  # Adatta la forma all'intero dataset

# Primo encoder
encoder_1 = SelfAttention(num_heads=num_heads, head_dim=head_dim)(input_layer)
encoder_1 = Dense(128, activation='relu')(encoder_1)
encoder_1 = Dense(128, activation='relu')(encoder_1)

# Secondo encoder
encoder_2 = SelfAttention(num_heads=num_heads, head_dim=head_dim)(encoder_1)
encoder_2 = Dense(64, activation='relu')(encoder_2)
encoder_2 = Dense(64, activation='relu')(encoder_2)

# Concatena l'output dei due encoder
concatenated_output = Concatenate()([encoder_1, encoder_2])

# Output layer
output_layer = Dense(num_features)(concatenated_output)

# Aggiungi l'output layer al modello
transformer_model = tf.keras.Model(inputs=input_layer, outputs=output_layer, name='Transformer')


# Creazione del modello con self-attention e più strati
transformer_model.compile(loss='mse',
              optimizer=Adam(learning_rate=0.00001),
              metrics=['mean_absolute_error'])

# Definisci gli input per i due modelli
input_layer = Input(shape=(None, 5))

# Ottieni le uscite dai modelli Bi-LSTM e Transformer
bi_lstm_output = bi_lstm_attention_model(input_layer)
transformer_output = transformer_model(input_layer)

# Calcola i pesi dell'attenzione
attention_weights = Dense(1, activation='sigmoid')(bi_lstm_output)
# Moltiplica le uscite dei modelli per i pesi dell'attenzione
weighted_bi_lstm_output = Multiply()([bi_lstm_output, attention_weights])
weighted_transformer_output = Multiply()([transformer_output, 1 - attention_weights])

# Combina le uscite pesate
combined_outputs = Add()([weighted_bi_lstm_output, weighted_transformer_output])

# Aggiungi strati densi per elaborare le uscite combinate
combined_outputs = Dense(256, activation='relu')(combined_outputs)
combined_outputs = Dense(128, activation='relu')(combined_outputs)
combined_outputs = Dense(64, activation='relu')(combined_outputs)
combined_outputs = Dense(5)(combined_outputs)

# Crea il modello ibrido
hybrid_model = Model(inputs=input_layer, outputs=combined_outputs)

# Stampa un riassunto del modello
hybrid_model.summary()

# Compila il modello ibrido
hybrid_model.compile(loss='mse', optimizer=Adam(learning_rate=0.00001), metrics=['mean_absolute_error'])

# Aggiunta di un callback per ridurre il tasso di apprendimento su plateau
lr_scheduler = ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=10, verbose=1, min_lr=1e-6)
callbacks = [lr_scheduler]

# Esempio di utilizzo nei fit e predict del modello
history = hybrid_model.fit(X_train_3d, y_train_3d, validation_data=(X_val_3d, y_val_3d),
                                      epochs=150,
                                      batch_size=64,
                                      callbacks=callbacks,
                                      verbose=1)
predictions_val = hybrid_model.predict(X_val_3d)
predictions_test = hybrid_model.predict(X_test_3d)


# Valuta il modello sull'insieme di test
test_loss, test_mae = hybrid_model.evaluate(X_test_3d, y_test_3d, verbose=0)

# Riduci le dimensioni di y_test_3d a (1006, 5)
y_test_2d = y_test_3d.reshape(-1, 5)

# Rimuovi il terzo asse dalle previsioni
predictions_test_squeezed = np.squeeze(predictions_test)

# Calcola il RMSE
rmse = np.sqrt(mean_squared_error(y_test_2d, predictions_test_squeezed))

# Calcola il R-squared (R²)
r2 = r2_score(y_test_2d, predictions_test_squeezed)

print(f'Test Loss: {test_loss}')
print(f'Test Mean Absolute Error (MAE): {test_mae}')
print(f'Test Root Mean Squared Error (RMSE): {rmse}')
print(f'Test R-squared (R²): {r2}')

# Creazione dei grafici delle learning curve
plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.title('Training and Validation Loss')

plt.subplot(1, 2, 2)
plt.plot(history.history['mean_absolute_error'], label='Training MAE')
plt.plot(history.history['val_mean_absolute_error'], label='Validation MAE')
plt.xlabel('Epoch')
plt.ylabel('Mean Absolute Error')
plt.legend()
plt.title('Training and Validation Mean Absolute Error')

plt.tight_layout()
plt.show()

# Trova l'indice dell'epoca con la minima val_loss e loss
best_epoch_val = np.argmin(history.history['val_loss'])
best_epoch = np.argmin(history.history['loss'])
# Trova il valore minimo della val_loss e loss
best_val_loss = history.history['val_loss'][best_epoch_val]
best_loss = history.history['loss'][best_epoch]
# Stampa il risultato
print(f'Best Validation Loss: {best_val_loss:.4f} at epoch {best_epoch_val + 1}')
print(f'Best Training Loss: {best_loss:.4f} at epoch {best_epoch + 1}')

feature_names = ['Close', 'Open', 'High', 'Low']  # Escludi la feature 'Volume'

plt.figure(figsize=(12, 24))  # Imposta la dimensione complessiva del grafico

total_train_samples = len(y_train)
total_val_samples = len(y_val)
total_test_samples = len(y_test)


# Estrai le date dei dati di addestramento e validazione
dates_train = df.index[:total_train_samples]
dates_val = df.index[total_train_samples:total_train_samples + total_val_samples]
dates_test = df.index[total_train_samples + total_val_samples:]

# Creazione dei grafici delle previsioni per ciascuna feature
for feature_index, feature_name in enumerate(feature_names):
    plt.figure(figsize=(12, 4))

    # Estrai i dati reali e le previsioni per la caratteristica specifica
    y_train_feature = y_train_3d[:, 0, feature_index]
    y_val_feature = y_val_3d[:, 0, feature_index]
    predictions_val_feature = predictions_val[:, 0, feature_index]
    y_test_feature = y_test_3d[:, 0, feature_index]
    predictions_test_feature = predictions_test[:, 0, feature_index]

    plt.plot(dates_train, y_train_feature, color='blue', label=f'Dati Reali di Training {feature_name}', linewidth=2.5)
    plt.plot(dates_val, y_val_feature, color='orange', label=f'Dati Reali di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_val, predictions_val_feature, color='red', label=f'Previsioni di Validazione {feature_name}', linewidth=2.5)
    plt.plot(dates_test, y_test_feature, color='yellow', label=f'Dati Reali di Test {feature_name}', linewidth=2.5)
    plt.plot(dates_test, predictions_test_feature, color='green', label=f'Previsioni di Test {feature_name}', linewidth=2.5)

    plt.xlabel('Data')
    plt.ylabel('Valore')
    plt.title(f'Confronto tra Previsioni e Dati Reali di {feature_name}')
    plt.legend()
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()

# Crea un DataFrame da y_val con nomi di colonne appropriati
y_val_df = pd.DataFrame(y_val_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_val_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_val_df = pd.DataFrame(predictions_val[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_val_df)
# Crea un DataFrame da y_val con nomi di colonne appropriati
y_test_df = pd.DataFrame(y_test_3d[:, 0, :], columns=['Actual Close', 'Actual Open', 'Actual High', 'Actual Low', 'Actual Volume'])
print(y_test_df)
# Crea un nuovo DataFrame con le colonne di previsione
predictions_test_df = pd.DataFrame(predictions_test[:, 0, :], columns=['Prediction Close', 'Prediction Open', 'Prediction High', 'Prediction Low', 'Prediction Volume'])
print(predictions_test_df)
# Unisci i due DataFrame in uno solo
combined_df = pd.concat([y_val_df, predictions_val_df], axis=1)

# Stampa il DataFrame risultante
#print(combined_df)

#--------------------stampare un grafico del modello-------------------------------------------------
plot_model(hybrid_model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)