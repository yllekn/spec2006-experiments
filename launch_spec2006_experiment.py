import os
import sys
from uuid import UUID

from gem5art.artifact import Artifact
from gem5art.run import gem5Run
from gem5art.tasks.tasks import run_gem5_instance
from gem5art.tasks.tasks import run_job_pool

experiments_repo = Artifact.registerArtifact(
    command = '''
        git clone https://gem5.googlesource.com/public/gem5-resources
        cd gem5-resources
        git checkout cee972a1727abd80924dad73d9f3b5cf0f13012d
        cd src/spec-2006
        git init
        git remote add origin https://github.com/yllekn/spec2006-experiments.git 
    ''',
    typ = 'git repo',
    name = 'spec2006 Experiment',
    path =  './',
    cwd = './',
    documentation = '''
        local repo to run spec 2006 experiments with gem5 full system mode;
        resources cloned from https://gem5.googlesource.com/public/gem5-resources upto commit cee972a1727abd80924dad73d9f3b5cf0f13012d of stable branch
    '''
)

gem5_repo = Artifact.registerArtifact(
    command = '''
        git clone -b v20.1.0.2 https://gem5.googlesource.com/public/gem5
        cd gem5
        scons build/X86/gem5.opt -j8
    ''',
    typ = 'git repo',
    name = 'gem5',
    path =  'gem5/',
    cwd = './',
    documentation = 'cloned gem5 v20.1.0.2'
)


gem5_binary = Artifact.registerArtifact(
    command = 'scons build/X86/gem5.opt -j8',
    typ = 'gem5 binary',
    name = 'gem5-20.1.0.2',
    cwd = 'gem5/',
    path =  'gem5/build/X86/gem5.opt',
    inputs = [gem5_repo,],
    documentation = 'compiled gem5 v20.1.0.2 binary'
)

m5_binary = Artifact.registerArtifact(
    command = 'scons build/x86/out/m5',
    typ = 'binary',
    name = 'm5',
    path =  'gem5/util/m5/build/x86/out/m5',
    cwd = 'gem5/util/m5',
    inputs = [gem5_repo,],
    documentation = 'm5 utility'
)

packer = Artifact.registerArtifact(
    command = '''
        wget https://releases.hashicorp.com/packer/1.6.6/packer_1.6.6_linux_amd64.zip;
        unzip packer_1.6.6_linux_amd64.zip;
    ''',
    typ = 'binary',
    name = 'packer',
    path =  'disk-image/packer',
    cwd = 'disk-image',
    documentation = 'Program to build disk images. Downloaded from https://www.packer.io/.'
)

disk_image = Artifact.registerArtifact(
    command = './packer build spec-2006/spec-2006.json',
    typ = 'disk image',
    name = 'spec-2006',
    cwd = 'disk-image/',
    path = 'disk-image/spec-2006/spec-2006-image/spec-2006',
    inputs = [packer, experiments_repo, m5_binary,],
    documentation = 'Ubuntu Server with SPEC 2006 installed, m5 binary installed and root auto login'
)

linux_binary = Artifact.registerArtifact(
    name = 'vmlinux-4.19.83',
    typ = 'kernel',
    path = './vmlinux-4.19.83',
    cwd = './',
    command = ''' wget http://dist.gem5.org/dist/v20-1/kernels/x86/static/vmlinux-4.19.83''',
    inputs = [experiments_repo,],
    documentation = "kernel binary for v4.19.83",
)

if __name__ == "__main__":
    cpus = ['kvm', 'atomic', 'o3', 'timing']
    benchmark_sizes = {'kvm':    ['test', 'ref'],
                       'atomic': ['test'],
                       'o3':     ['test'],
                       'timing': ['test']
                      }
    benchmarks = ['401.bzip2','403.gcc','410.bwaves','416.gamess','429.mcf',
                  '433.milc','434.zeusmp','435.gromacs','436.cactusADM',
                  '437.leslie3d','444.namd','445.gobmk','453.povray',
                  '454.calculix','456.hmmer','458.sjeng','459.GemsFDTD',
                  '462.libquantum','464.h264ref','465.tonto','470.lbm',
                  '471.omnetpp','473.astar','481.wrf','482.sphinx3',
                  '998.specrand','999.specrand']

    jobs = []
    for cpu in cpus:
        for size in benchmark_sizes[cpu]:
            for benchmark in benchmarks:
                run = gem5Run.createFSRun(
                    'gem5 19 spec 2006 experiment', # name
                    'gem5/build/X86/gem5.opt', # gem5_binary
                    'configs/run_spec.py', # run_script
                    'results/{}/{}/{}'.format(cpu, size, benchmark), # relative_outdir
                    gem5_binary, # gem5_artifact
                    gem5_repo, # gem5_git_artifact
                    experiments_repo, # run_script_git_artifact
                    'vmlinux-4.19.83', # linux_binary
                    'disk-image/spec-2006/spec-2006-image/spec-2006', # disk_image
                    linux_binary, # linux_binary_artifact
                    disk_image, # disk_image_artifact
                    cpu, "classic", benchmark, size, # params
                    timeout = 5*24*60*60 # 5 days
                )
                jobs.append(run)
                run_gem5_instance.apply_async((run,))
    run_job_pool(jobs)
