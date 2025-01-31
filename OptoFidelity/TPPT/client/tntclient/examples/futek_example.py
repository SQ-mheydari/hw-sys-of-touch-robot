import tntclient.tnt_client as tnt_client

# The client is used to create different client objects for other things like DUTs and robot
client = tnt_client.TnTClient()

# In this example Futek is created
futek = client.futek('futek')

# It is possible to tare (remove tool's own weight from measurements) Futek through the client.
futek.tare()

print("Tare completed")

# Get values from Futek in a loop.
while True:
    try:
        # forcevalue() returns the tared force value from Futek.
        print(futek.forcevalue())
    except:
        print("Problem when getting a value from Futek. Are you sure that real Futek is used instead of simulator?"
              "Please check that Futek is connected and working.")
