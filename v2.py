# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
from torch.nn import functional as F
torch.manual_seed(1337)

batch_size = 32
block_size = 8
max_iters = 10000
eval_interval = 300
learning_rate = 1e-3
device = 'cpu'
eval_iters = 200
n_embd = 32



# read it in to inspect it
with open('input.txt', 'r', encoding='utf-8') as f:
    text = f.read()


chars = sorted(list(set(text)))
vocab_size = len(chars)
print(''.join(chars))
print(vocab_size)

# create a mapping from characters to integers
stoi = { ch:i for i,ch in enumerate(chars) }
itos = { i:ch for i,ch in enumerate(chars) }
encode = lambda s: [stoi[c] for c in s] # encoder: take a string, output a list of integers
decode = lambda l: ''.join([itos[i] for i in l]) # decoder: take a list of integers, output a string


data = torch.tensor(encode(text), dtype=torch.long)
n = int(0.9*len(data)) # first 90% will be train, rest val
train_data = data[:n]
val_data = data[n:]


def get_batch(split):
    # generate a small batch of data of inputs x and targets y
    data = train_data if split == 'train' else val_data
    ix = torch.randint(len(data) - block_size, (batch_size,))
    x = torch.stack([data[i:i+block_size] for i in ix])
    y = torch.stack([data[i+1:i+block_size+1] for i in ix])
    return x, y




@torch.no_grad()
def estimate_loss():
   out= {}
   model.eval()
   for split in ['train', 'val']:
      losses = torch.zeros(eval_iters)
      for k in range(eval_iters):
         x, y = get_batch(split)
         logits, loss = model(x, y)
         losses[k] = loss.item()
      out[split] = losses.mean()
   model.train()
   return out


class Head(nn.Module):
    """One Head of a self attention"""
    def __init__(self, head_size):
      super().__init__()
      self.query = nn.Linear(n_embd, head_size)
      self.key = nn.Linear(n_embd, head_size)
      self.value = nn.Linear(n_embd, head_size)
      self.register_buffer('tril', torch.tril(torch.ones(block_size, block_size)))
    
    def forward(self, x):
      B,T,C = x.shape
      q = self.query(x) # (B,T,H)
      k = self.key(x) # (B,T,H)
      v = self.value(x) # (B,T,H)

      weights = q @ k.transpose(-2,-1) * C**-0.5
      weights = weights.masked_fill(self.tril[:T, :T] == 0, float('-inf'))
      weights = F.softmax(weights, dim=-1) # (B,T,T)

      out = weights @ v

      return out  
    

class MultiHeadAttention(nn.Module):
    """Multi-Head Self Attention"""
    def __init__(self, n_heads, head_size):
      super().__init__()
      self.heads = nn.ModuleList([Head(head_size) for _ in range(n_heads)])
    
    def forward(self, x):
       return torch.cat([h(x) for h in self.heads], dim = -1)



class BigramLanguageModel(nn.Module):

  def __init__(self, vocab_size):
    super().__init__()
    # each token directly reads off the logits for the next token from a lookup table
    self.token_embedding_table = nn.Embedding(vocab_size, n_embd)
    self.positional_embedding_table = nn.Embedding(block_size, n_embd)
    self.sa_head = MultiHeadAttention(4, n_embd//4)
    self.lm_head = nn.Linear(n_embd, vocab_size)

  def forward(self, idx, targets=None):
    B, T = idx.shape

    # idx and targets are both (B,T) tensor of integers
    token_embeddings = self.token_embedding_table(idx) # (B,T,C)
    pos_embeddings = self.positional_embedding_table(torch.arange(T, device=device)) # T, C
    embeddings = token_embeddings + pos_embeddings # (B,T,C)
    
    x = self.sa_head(embeddings)
    
    logits = self.lm_head(x)
    if targets is None:
        loss = None
    else:
        B, T, C = logits.shape
        logits = logits.view(B*T, C)
        targets = targets.view(B*T)
        loss = F.cross_entropy(logits, targets)

    return logits, loss

    return logits

  def generate(self, idx, max_new_tokens):
    for _ in range(max_new_tokens):
      # forward pass

      idx_cond = idx[:, -block_size:]
      logits, loss = self(idx_cond)
      logits = logits[:, -1, :]
      probs = F.softmax(logits, dim=-1) # (B, C)
      idx_next = torch.multinomial(probs, num_samples=1)
      idx = torch.cat((idx, idx_next), dim=1) # (B, T+1)

    return idx



model = BigramLanguageModel(vocab_size)
m = model.to(device)

optimizer = torch.optim.AdamW(m.parameters(), lr=1e-3)

for iter in range(max_iters):

  if iter % eval_interval == 0:
      losses = estimate_loss()
      print(f'Iter {iter}: train loss {losses["train"]:.4f}, val loss {losses["val"]:.4f}')

  xb, yb = get_batch('train')
  logits, loss = m(xb,yb)
  optimizer.zero_grad(set_to_none=True)
  loss.backward()
  optimizer.step()

context = torch.zeros((1,1), dtype = torch.long, device=device)
print(decode(m.generate(context, max_new_tokens = 500)[0].tolist()))

