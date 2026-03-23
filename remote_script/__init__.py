from .WacomKaoss import WacomKaoss

def create_instance(c_instance):
    return WacomKaoss(c_instance)
