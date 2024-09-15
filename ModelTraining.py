import tensorflow as tf
import tensorflow_datasets as tfds
# Define your model function
def create_emg_model(input_shape, num_classes):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=input_shape),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(num_classes, activation='softmax')  
    ])
    return model

train_ds = tfds.load('Gail Rest.xlsx', split = 'train[:80%]')
test_ds = tfds.load('Gail Rest.xlsx', split = 'test[:20%]')

print(train_ds)
# # Define input shape and number of classes
# input_shape = (8,)
# num_classes = 1

# # Create the model
# model = create_emg_model(input_shape, num_classes)

# # Compile the model
# model.compile(optimizer='adam',
#               loss='sparse_categorical_crossentropy',
#               metrics=['accuracy'])

# # Train the model
# model.fit(train_ds, test_ds, epochs=10, batch_size=32, validation_data=(train_ds, test_ds))

# # Evaluate the model
# test_loss, test_acc = model.evaluate(train_ds, test_ds)
# print('Test accuracy:', test_acc)

# # Save the model
# model.save('emg_model.h5')
