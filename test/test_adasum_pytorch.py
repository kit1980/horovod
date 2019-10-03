import torch
import horovod.torch as hvd
import numpy as np
import time
from horovod.torch.mpi_ops import synchronize
from horovod.torch.mpi_ops import AllreduceType

hvd.init()

device = torch.device('cuda', hvd.local_rank())
np.random.seed(2)
torch.manual_seed(2)
size = hvd.size()
local_size = hvd.local_size()
rank = hvd.rank()

data_type = np.float32

def test_orthogonal():
  all_Ns = [size*20 - 17, size*2+1, size+2]
  tensors = []
  all_qs = []
  for N in all_Ns:
    a = np.random.normal(0, 1, (N,size)).astype(np.float64)
    q, r = np.linalg.qr(a)
    q = q.astype(data_type)
    all_qs.append(q)
    tensors.append(q[:,hvd.rank()])

  tensors = list(map(lambda x: torch.from_numpy(x).to(device), tensors))

  handles = [
    hvd.allreduce_async(tensor, average=False, allreduce_type=AllreduceType.Adasum)
    for tensor in tensors
  ]

  reduced_tensors = [synchronize(h) for h in handles]

  expected = [np.sum(q,axis=1) for q in all_qs]
  all_comp = [np.alltrue(np.isclose(e, rt.cpu().numpy())) for e,rt in zip(expected,reduced_tensors)]
  if np.alltrue(all_comp):
    print('Orthogonal test passed')
  else:
    for c,e,rt in zip(all_comp, expected, reduced_tensors):
      if c == False:
        print('computed: ', rt)
        print('expected: ', e)
        print(np.isclose(e, rt.cpu().numpy()))
  
def test_parallel():
  all_Ns = [size*20 - 13, size*2+1, size+2]
  tensors = []
  all_qs = []
  for N in all_Ns:
    a = np.random.normal(0, 1, (N, 1)).astype(np.float64)
    r = np.random.normal(0, 1, (size, 1)).astype(np.float64)
    q = np.dot(a,r.T)
    q = q.astype(data_type)
    all_qs.append(q)
    tensors.append(q[:,hvd.rank()])

  tensors = list(map(lambda x: torch.from_numpy(x).to(device), tensors))

  handles = [
    hvd.allreduce_async(tensor, average=False, allreduce_type=AllreduceType.Adasum)
    for tensor in tensors
  ]

  reduced_tensors = [synchronize(h) for h in handles]

  expected = [np.sum(q,axis=1)/(size/local_size) for q in all_qs]
  all_comp = [np.alltrue(np.isclose(e, rt.cpu().numpy())) for e,rt in zip(expected,reduced_tensors)]
  if np.alltrue(all_comp):
    print('Parallel test passed')
  else:
    for c,e,rt in zip(all_comp, expected, reduced_tensors):
      if c == False:
        print('computed: ', rt)
        print('expected: ', e)
        print(np.isclose(e, rt.cpu().numpy()))
  
if __name__ == '__main__':
  test_orthogonal()
  test_parallel()
