# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
from torch.nn import functional as F
torch.manual_seed(1337)
import torch.autograd.profiler as profiler
batch_size = 64
block_size = 256
max_iters = 5000
eval_interval = 500
learning_rate = 5e-4
device = torch.device("mps")
# device = 'cpu'
eval_iters = 200
n_embd = 256
n_head = 8
n_layer = 6
dropout = 0.2

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
data = data.to(device)
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
      self.dropout = nn.Dropout(dropout)

    
    def forward(self, x):
      B,T,C = x.shape
      q = self.query(x) # (B,T,H)
      k = self.key(x) # (B,T,H)
      v = self.value(x) # (B,T,H)

      weights = q @ k.transpose(-2,-1) * C**-0.5
      weights = weights.masked_fill(self.tril[:T, :T] == 0, float('-inf'))
      weights = F.softmax(weights, dim=-1) # (B,T,T)
      weights = self.dropout(weights)

      out = weights @ v

      return out  
    

class MultiHeadAttention(nn.Module):
    """Multi-Head Self Attention"""
    def __init__(self, n_heads, head_size):
      super().__init__()
      self.heads = nn.ModuleList([Head(head_size) for _ in range(n_heads)])
      self.proj = nn.Linear(n_embd, n_embd)
      self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
       x =  torch.cat([h(x) for h in self.heads], dim = -1)
       return self.dropout(self.proj(x))  # (B,T,C)


class FeedForward(nn.Module):
    def __init__(self, n_embd):
      super().__init__()
      self.net = nn.Sequential(
          nn.Linear(n_embd, 4*n_embd),
          nn.ReLU(),
          nn.Linear(n_embd*4, n_embd),
          nn.Dropout(dropout)
      )
    
    def forward(self, x):
      return self.net(x)
    


class Block(nn.Module):
   def __init__(self, n_embd, n_head):
      super().__init__()
      self.sa_head = MultiHeadAttention(n_head, n_embd//n_head)
      self.ffwd = FeedForward(n_embd)
      self.ln1 = nn.LayerNorm(n_embd)
      self.ln2 = nn.LayerNorm(n_embd)
      
   
   def forward(self, x):
      x = x + self.sa_head(self.ln1(x))
      x = x + self.ffwd(self.ln2(x))  # (B,T,C)
      return x

      


class BigramLanguageModel(nn.Module):

  def __init__(self, vocab_size):
    super().__init__()
    # each token directly reads off the logits for the next token from a lookup table
    self.token_embedding_table = nn.Embedding(vocab_size, n_embd)
    self.positional_embedding_table = nn.Embedding(block_size, n_embd)
    self.blocks = nn.Sequential( *[Block(n_embd, n_head) for _ in range(n_layer)] )
    self.lm_head = nn.Linear(n_embd, vocab_size)
    self.ln_f = nn.LayerNorm(n_embd)

  def forward(self, idx, targets=None):
    B, T = idx.shape

    # idx and targets are both (B,T) tensor of integers
    token_embeddings = self.token_embedding_table(idx) # (B,T,C)
    pos_embeddings = self.positional_embedding_table(torch.arange(T, device=device)) # T, C
    embeddings = token_embeddings + pos_embeddings # (B,T,C)
    x = self.blocks(embeddings)
    x = self.ln_f(x)
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
print(decode(m.generate(context, max_new_tokens = 5000)[0].tolist()))

