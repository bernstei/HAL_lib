import numpy as np

def print_errors(IP, al, data_keys):
    E_DFT = [at.info[data_keys["E"]]/len(at) for at in al]
    F_DFT = []
    for at in al:
        F_DFT.extend(at.arrays[data_keys["F"]])

    E_ACE = []
    F_ACE = []

    for at in al:
        at.set_calculator(IP)
        E_ACE.append(at.get_potential_energy()/len(at))
        F_ACE.extend(at.get_forces())

    E_RMSE = np.sqrt(np.mean(np.power(np.array(E_DFT) - np.array(E_ACE), 2)))
    F_RMSE = np.sqrt(np.mean(np.power(np.asarray(F_DFT) - np.asarray(F_ACE), 2)))

    print("============================================")
    print("|  E   : {} meV/at |  F  :  {}  eV/A |".format(str(E_RMSE*1E3)[:5], str(F_RMSE)[:5]))
    print("============================================")