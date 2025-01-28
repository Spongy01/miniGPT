# miniGPT

**miniGPT** is a personal learning project designed to explore the fundamentals of text generation using language models. The project includes experiments with a bigram character-level model and a small-scale GPT-2-like transformer model, implemented from scratch using PyTorch.

This project serves as an introduction to the field of language models and text generation. It helped me understand the underlying mechanics of how language models work and how transformers generate text based on context.

## Features
- **Bigram Character-Level Model**: Generates text using a simple probabilistic approach based on bigrams.
- **Small-Scale GPT-2-like Model**: Implements transformers with attention mechanisms to generate text by predicting the next character based on the context.
- **Dataset**: Utilizes the miniShakespeare dataset for training and testing.
- **Contextual Text Generation**: Includes a configurable block size for the context used in generating the next character.

## Technologies Used
- **PyTorch**: For implementing and training the models.

## How It Works
- A block of text is used as the context for the model to generate the next character.
- The bigram model uses probabilities based on character pairs, while the GPT-2-like model employs a transformer architecture with attention mechanisms for more sophisticated predictions.
- The models are trained on the miniShakespeare dataset to learn patterns and generate coherent text.

## Learnings
- Gained a foundational understanding of:
  - Attention mechanisms.
  - Transformer architecture.
  - How text generation is achieved in language models.
- Learned how to implement these concepts from scratch using PyTorch.



---

Feel free to explore the code and experiment with it!

