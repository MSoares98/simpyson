import ase.io
import numpy as np
import scipy.constants as const


def read_vasp(file, format):
    filename = ase.io.read(file, format=format)
    n_atoms = filename.get_global_number_of_atoms()
    np.set_printoptions(suppress=True)
    efg = []
    sym_tensor = []
    const_shield = []
    core_shield_dict = []
    ms = []
    volume = None
    with open(file, 'r') as outcar:
        lines = outcar.readlines()
        #Find lines with specific header
        for line in lines:
            if line.find("Electric field gradients (V/A^2)") != -1:
                idx_header1 = lines.index(line) #efg
            if line.find("SYMMETRIZED TENSORS") != -1:
                idx_header2 = []
                idx_header2.append(lines.index(line)) #sym tensor - need to take second one (unsym. tensors)
            if line.find("G=0 CONTRIBUTION TO CHEMICAL SHIFT") != -1:
                idx_header3 = lines.index(line) #constant shielding
            if line.find('Core NMR properties') != -1:
                idx_header4 = lines.index(line) #core NMR prop - depends on atom type
            if line.find("Core contribution to magnetic susceptibility:") != -1:
                val = line.split()[5]
                exp = line.split()[6][-2:]
                mag_sus = float(val)*10**int(exp)
            if line.find("volume of cell") != -1 and volume is None:
                volume = float(line.split()[4])

        chi_fact = 3.0/8.0/np.pi*volume*6.022142e23/1e24 # Conversion factor for magnetic susceptibility
        
        #Calculate tensors for every atoms
        for i in range(n_atoms):
            grad = (lines[idx_header1+4+i]).split()[1:] # V_xx, V_yy, V_zz, V_xy, V_xz, V_yz
            matrix = np.array([[grad[0],grad[3],grad[4]],   #xx xy xz
                               [grad[3],grad[1],grad[5]],   #xy yy yz
                               [grad[4],grad[5],grad[2]]])  #xz yz zz
            efg.append(matrix)

        for i in range(n_atoms*4):
            if i % 4 != 0:
                sym=lines[idx_header2[-1] + i + 1].split()
                sym_tensor.append(lines[idx_header2[-1] + i + 1].split())

        for i in range(3):
            const_shield.append((lines[idx_header3 + 4 + i]).split()[1:])

        for i in range(len(np.unique(filename.get_chemical_symbols()))):
            core_shield_dict.append((lines[idx_header4 + 4 + i]).split()[1:])
        core_shield_dict = dict((k[0], float(k[1:][0])) for k in core_shield_dict)
        core_shield = []

        for i in filename.get_chemical_symbols():
            core_shield.append(core_shield_dict[i])

    #Process results
    efg = np.array(efg,dtype=float) #resulting EFG matrix
    efg = efg * 1e20 / const.physical_constants["atomic unit of electric field gradient"][0]
    sym_tensor = np.split(np.array(sym_tensor,dtype=float), n_atoms) #symmetry tensors
    const_shield = np.array(const_shield, dtype=float) #constant shielding of the lattice
    core_shield = np.array(core_shield,dtype=float) #core shielding depending on atom type
    
    for i in range(n_atoms):
        core_diag = np.diag(core_shield[i] * np.ones(3))
        ms_tensor = sym_tensor[i] + const_shield + core_diag + mag_sus/chi_fact*1e6*np.eye(3) #calculating MS tensor
        ms.append(-ms_tensor)  # calculating MS tensors
    ms=np.array(np.array(ms).tolist(),dtype=float) #processing MS tensor to work with ase

    filename.set_array('efg', efg)
    filename.set_array('ms', ms)

    return filename