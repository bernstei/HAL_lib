#load Julia and Python dependencies
from julia.api import Julia
jl = Julia(compiled_modules=False)

from julia import Main
from HAL_lib import ace_basis
Main.eval("using ASE, JuLIP, ACE1")

import numpy as np

from julia.JuLIP import energy, forces, virial
convert = Main.eval("julip_at(a) = JuLIP.Atoms(a)")
ASEAtoms = Main.eval("ASEAtoms(a) = ASE.ASEAtoms(a)")

def assemble_lsq(B, E0s, atoms_list, data_keys, weights):
    num_obs = np.sum([1 + len(at)*3 + 9 for at in atoms_list])
    len_B = Main.eval("length(B)")

    Psi = np.zeros((num_obs, len_B))
    Y = np.zeros(num_obs)

    i = 0
    for at in atoms_list:
        Psi[i,:] = weights["E"] * np.array(energy(B, convert(ASEAtoms(at)))).flatten() 
        Y[i] = weights["E"] * (np.array(at.info[data_keys["E"]]).flatten() - np.sum([at.get_chemical_symbols().count(EL) * E0 for EL, E0 in E0s.items()]))
        i += 1

        Frows = len(at)*3
        Psi[i:i+Frows, :] = weights["F"] * np.reshape(np.array(forces(B, convert(ASEAtoms(at)))).flatten(), (len_B, Frows)).transpose()
        Y[i:i+Frows] = weights["F"] * np.array(at.arrays[data_keys["F"]]).flatten()
        i += Frows

        try:
            Vrows = 9
            Psi[i:i+Vrows, :] = weights["V"] * np.reshape(np.array(virial(B, convert(ASEAtoms(at)))).flatten(), (len_B, Vrows)).transpose()
            Y[i:i+Vrows] = weights["V"] * np.array(at.info[data_keys["V"]]).flatten()
            i += Vrows
        except:
            pass

    return Psi, Y

def add_lsq(B, E0s, at, data_keys, weights, Psi, Y):
    extra_obs = np.sum([1 + len(at)*3 + 9])
    len_B = Main.eval("length(B)")

    row_count = np.shape(Psi)[0]
    Psi = np.append(Psi, np.zeros((extra_obs, len_B)), axis=0)
    Y = np.append(Y, np.zeros(extra_obs))

    Psi[row_count, :] = weights["E"] * np.array(energy(B, convert(ASEAtoms(at)))).flatten() 
    Y[row_count] = weights["E"] * (np.array(at.info[data_keys["E"]]).flatten() - np.sum([at.get_chemical_symbols().count(EL) * E0 for EL, E0 in E0s.items()]))
    row_count += 1

    Frows = len(at)*3
    Psi[row_count:row_count+Frows, :] = weights["F"] * np.reshape(np.array(forces(B, convert(ASEAtoms(at)))).flatten(), (len_B, Frows)).transpose()
    Y[row_count:row_count+Frows] = weights["F"] * np.array(at.arrays[data_keys["F"]]).flatten()
    row_count += Frows

    try:
        Vrows = 9
        Psi[row_count:row_count+Vrows, :] = weights["V"] * np.reshape(np.array(virial(B, convert(ASEAtoms(at)))).flatten(), (len_B, Vrows)).transpose()
        Y[row_count:row_count+Vrows] = weights["V"] * np.array(at.info[data_keys["V"]]).flatten()
        i += Vrows
    except:
        pass

    return Psi, Y

def fit(Psi, Y, B, E0s, solver, ncomms=32):
    solver.fit(Psi, Y)
    c = solver.coef_
    sigma = solver.sigma_
    score = solver.scores_[-1]

    # Code below is for ARD solver, TO DO:
    if sigma.shape[0] != len(c):
        sigma_large = np.zeros((len(c), len(c)))
        non_zeros = np.nonzero(c)
        for (i, r_ind) in enumerate(non_zeros):
            r = np.zeros(len(c))
            r[non_zeros] = sigma[:, i]
            sigma_large[r_ind, :] = r
        sigma = sigma_large
        #comms = np.random.multivariate_normal(c, 0.5*(sigma_large + sigma_large.T), size=ncomms)
    #else:

    sigma_min_eig_val = np.min(np.real(np.linalg.eigvals(sigma)))
    sigma_reg = sigma + (np.eye(sigma.shape[0]) * np.abs(sigma_min_eig_val) * 10)
    sigma_reg_min_eig_val = np.min(np.real(np.linalg.eigvals(sigma_reg)))

    print("sigma min eigval: {}, sigma_reg min eigval: {}, score: {}".format(sigma_min_eig_val, sigma_reg_min_eig_val, score))

    comms = np.random.multivariate_normal(c, sigma_reg, size=ncomms)
    
    IP, IPs = ace_basis.combine(B, c, E0s, comms)
    
    return IP, IPs



