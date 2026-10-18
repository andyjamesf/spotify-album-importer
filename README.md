# spotify-album-importer

Guarda na tua biblioteca do Spotify os álbuns de uma lista em CSV. O que não existir no catálogo do Spotify é ignorado e fica listado num relatório. Só usa a biblioteca padrão do Python 3, sem dependências.

*Saves the albums listed in a CSV (`artista,album`) to your Spotify library; anything not found is skipped and reported.*

## Formato do CSV

```csv
artista,album
Pink Floyd,The Wall
Tool,Ænima
Queen,
```

Uma linha sem álbum (como `Queen,`) só é usada com `--seguir-artistas`, que segue o artista.

## Passos

1. **Cria uma app no Spotify.** Vai a <https://developer.spotify.com/dashboard>, clica em *Create app* e preenche o nome e a descrição.
2. **Redirect URI:** `http://127.0.0.1:8888/callback`. Tem de ser exatamente isto, com `127.0.0.1` e não `localhost`.
3. **API:** escolhe apenas *Web API*, aceita os termos e guarda.
4. **Copia o Client ID** da app (em *Settings*). O Client ID não é secreto e este script não usa o Client Secret.
5. **Testa primeiro, sem guardar nada:**
   ```
   python3 spotify_album_importer.py exemplo.csv --client-id O_TEU_CLIENT_ID --teste
   ```
   O browser abre para autorizares. No fim, vê o `relatorio_spotify.txt` e confirma que os álbuns encontrados são os que queres. As correspondências são aproximadas e podem escolher uma edição diferente (deluxe, remaster) ou, raramente, um álbum errado.
6. **Corre a sério,** sem `--teste`:
   ```
   python3 spotify_album_importer.py a_minha_lista.csv --client-id O_TEU_CLIENT_ID
   ```
   Acrescenta `--seguir-artistas` para seguir também os artistas das linhas sem álbum.

Em vez de `--client-id` podes definir a variável de ambiente `SPOTIFY_CLIENT_ID`.

## Opções

| Opção | O que faz |
|---|---|
| `--client-id` | Client ID da tua app (ou `SPOTIFY_CLIENT_ID`) |
| `--teste` | Só procura e escreve o relatório, não altera a tua conta |
| `--seguir-artistas` | Segue os artistas das linhas sem álbum |
| `--relatorio` | Caminho do relatório (por omissão `relatorio_spotify.txt`) |

## Notas

- O login usa o fluxo OAuth com PKCE. O token só existe em memória durante a execução e não é guardado em disco.
- Se a app estiver em *development mode*, só as contas que adicionares em *User Management* podem autorizá-la.
- O script usa o endpoint `PUT /me/library` e, se a tua app o recusar, o antigo `PUT /me/albums`. A API do Spotify mudou recentemente e pode voltar a mudar.
- Para passar a biblioteca para o Apple Music, ferramentas como o Soundiiz fazem a transferência entre serviços. Não está testado aqui.

## Licença

MIT
