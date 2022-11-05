#load Julia and Python dependencies
from julia.api import Julia
jl = Julia(compiled_modules=False)
from julia import Main
Main.eval("using ASE, JuLIP, ACE1")

from HAL_lib import ACEcalculator
#from HAL_lib import HALcalculator
from HAL_lib import COcalculator

def full_basis(basis_info):
    Main.elements = basis_info["elements"]
    Main.cor_order = basis_info["cor_order"]
    Main.poly_deg_ACE = basis_info["poly_deg_ACE"]
    Main.poly_deg_pair = basis_info["poly_deg_pair"]
    Main.r_0 = basis_info["r0"]
    Main.r_in = basis_info["r_in"]
    Main.r_cut = basis_info["r_cut"]

    B = Main.eval("""
            Bsite = rpi_basis(species = Symbol.(elements),
                                N = cor_order,       # correlation order = body-order - 1
                                maxdeg = poly_deg_ACE,  # polynomial degree
                                r0 = r_0,     # estimate for NN distance
                                rin = r_in,
                                rcut = r_cut,   # domain for radial basis (cf documentation)
                                pin = 2)                     # require smooth inner cutoff

            Bpair = pair_basis(species = Symbol.(elements),
                                r0 = r_0,
                                maxdeg = poly_deg_pair,
                                rcut = r_cut + 1.0,
                                rin = 0.0,
                                pin = 0 )   # pin = 0 means no inner cutoff

            B = JuLIP.MLIPs.IPSuperBasis([Bpair, Bsite]);
            """)
    return B

def combine(B, c, E0s, comms):
    Main.E0s = E0s
    Main.ref_pot = Main.eval("refpot = OneBody(" + "".join([" :{} => {}, ".format(key, value) for key, value in E0s.items()]) + ")")
    Main.B = B
    Main.c = c
    Main.comms = comms
    Main.ncomms = len(comms)

    IP = Main.eval("ACE_IP = JuLIP.MLIPs.SumIP(ref_pot, JuLIP.MLIPs.combine(B, c))")
    Main.eval("Bpair_com = ACE1.committee_potential(Bpair, c[1:length(Bpair)], transpose(comms[:,1:length(Bpair)]))")
    Main.eval("Bsite_com = ACE1.committee_potential(Bsite, c[length(Bpair)+1:end], transpose(comms[:, length(Bpair)+1:end]))")
    IPs = Main.eval("CO_IP = JuLIP.MLIPs.SumIP(Bpair_com, Bsite_com)")
    return ACEcalculator.ACECalculator("ACE_IP"), COcalculator.COcalculator("CO_IP") 
    #return COcalculator.COCalculator("CO_IP")
    
