# (Opcional, avançado) Fonte "api": API oficial do Power BI com Azure

> Só use este caminho se você NÃO quiser depender do link público. Para o caminho simples, veja o README.md.

# Painel UMOE — modo API oficial

Este projeto consulta o Power BI **pela API oficial**, com uma identidade de aplicativo (sem login de pessoa, sem navegador, sem seu computador), monta o painel e publica numa página web **de hora em hora, 24 horas por dia**. Roda de graça no GitHub (Actions + Pages).

```
GitHub Actions (agendador, toda hora)
   └─ Power BI REST API (executeQueries / DAX)  ← identidade de aplicativo do Azure
        └─ gerador valida os números (se algo não bater, NÃO publica)
             └─ GitHub Pages:  https://SEU-USUARIO.github.io/NOME-DO-REPO/
                               └─ /api/v1/today.json  /month.json  (os JSON da API)
```

**Segurança dos números:** a cada execução o gerador confere que classes, centros de custo, frota e tipos de peça somam o total do dia, e que o total do dia bate com o histórico do mês. Se qualquer conferência falhar, ou o Power BI estiver fora do ar, a execução termina com erro **sem publicar** — a página anterior continua no ar e o GitHub avisa você por e-mail.

---

## O que você precisa (e quem faz o quê)

| Passo | Quem | Tempo |
|---|---|---|
| 1. Relatório num workspace compartilhado | você (Power BI) | 10 min |
| 2. Criar o aplicativo no Azure | você ou TI | 10 min |
| 3. Liberar o aplicativo no Power BI | **administrador do Power BI da UMOE** | 5 min |
| 4. Criar o repositório no GitHub e colar 3 segredos | você | 15 min |
| 5. Descobrir/conferir nomes e valores | você (3 cliques) | 10 min |

> Requisitos: licença **Power BI Pro** (ou Premium) para criar o workspace; um administrador que consiga ligar 2 chaves no portal de administração do Power BI. Se você não tem isso, use o texto da seção "Pedido para o TI" no final.

### Por que preciso mover o relatório?
Hoje ele está em **"Meu workspace"** (espaço pessoal). O Power BI **não permite** que aplicativos acessem o espaço pessoal de ninguém. Precisa estar num workspace compartilhado.

---

## Passo 1 — Colocar o relatório num workspace compartilhado

1. No Power BI (app.powerbi.com) → **Workspaces → Criar um workspace** → nome, por exemplo, `UMOE Dashboards`.
2. Publique o relatório lá:
   - Se você tem o arquivo `.pbix`: Power BI Desktop → **Publicar** → escolha `UMOE Dashboards`.
   - Se não tem: abra o relatório atual → **Arquivo → Baixar este arquivo** → abra no Desktop → **Publicar** → `UMOE Dashboards`.
3. No workspace novo, abra o **conjunto de dados (dataset) → Configurações**: refaça as credenciais da fonte de dados e **ligue a atualização agendada** (se a fonte exigir *gateway*, o computador do gateway precisa estar ligado — se for um servidor, está resolvido).
4. Anote os dois IDs, que aparecem na barra de endereço:
   - **ID do workspace**: `.../groups/`**`xxxxxxxx-xxxx-...`**`/reports/...`
   - **ID do dataset**: abra o dataset (Configurações) → `.../datasets/`**`xxxxxxxx-xxxx-...`**`/details`

## Passo 2 — Criar o aplicativo no Azure

1. portal.azure.com → **Microsoft Entra ID → Registros de aplicativo → Novo registro**. Nome: `painel-umoe`. Tipo: *somente este diretório*. Registrar.
2. Na página do aplicativo, copie: **ID do aplicativo (cliente)** e **ID do diretório (locatário)**. (Seu locatário aparece na URL do Power BI como `ctid=aca5c8c2-df2c-4cda-91c1-23eb0017d8cd`.)
3. **Certificados e segredos → Novo segredo do cliente** → validade 24 meses → copie o **Valor** (só aparece uma vez!).
4. **Não** adicione permissões de API (não são necessárias).
5. Entra ID → **Grupos → Novo grupo** (tipo *Segurança*), nome `painel-umoe-apps`, e adicione o aplicativo `painel-umoe` como membro.

## Passo 3 — Liberar no Power BI (precisa ser administrador)

Portal de administração do Power BI (engrenagem → *Portal de administração → Configurações de locatário*):

1. **Configurações do desenvolvedor → "Entidades de serviço podem usar APIs do Fabric/Power BI"** → *Habilitado* → *Grupos de segurança específicos* → `painel-umoe-apps`.
2. **Configurações de integração → "API REST de Execução de Consultas de Conjunto de Dados"** → *Habilitado*.
3. No workspace `UMOE Dashboards` → **Gerenciar acesso → Adicionar pessoas ou grupos** → `painel-umoe-apps` com a função **Membro**.

(As configurações podem levar até ~15 minutos para valer.)

## Passo 4 — GitHub

1. Crie conta em github.com (grátis) → **New repository** → nome `painel-umoe` → **Public** (necessário para o Pages grátis; o *código* é público, os *segredos* não).
2. Envie todos os arquivos desta pasta (botão *Add file → Upload files*, arrastando as pastas inclusive `.github`).
3. **Settings → Secrets and variables → Actions → New repository secret** — crie 3:
   - `PBI_TENANT_ID` = ID do diretório (locatário)
   - `PBI_CLIENT_ID` = ID do aplicativo (cliente)
   - `PBI_CLIENT_SECRET` = o Valor do segredo
4. Edite `config.json` no GitHub (ícone de lápis) e troque `COLE-AQUI-O-ID-DO-WORKSPACE` e `COLE-AQUI-O-ID-DO-DATASET` pelos IDs do Passo 1.
5. **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Passo 5 — Conferir (não pule!)

1. Aba **Actions → "Descobrir modelo" → Run workflow**. Abra a execução e veja a lista `TABELA | COLUNA`. Se o nome da tabela não for `Materiais`, ou se alguma coluna tiver nome diferente, ajuste `table` e `columns` em `config.json`. Se **"Valor Total" for uma medida** (não uma coluna), preencha `"value_expr": "[Valor Total]"`.
2. Aba **Actions → "Verificar valores" → Run workflow**. Ele compara os totais de 01 a 07/10 com os que lemos à mão no relatório (R$ 56.428, 266.031, 15.519, 0, 99.825, 38.121, 126.391). **Todas as linhas devem dizer `OK`.** Se não, o mapeamento está errado — não ligue o automático ainda; me mande a saída.
   - Diferença pequena num dia antigo pode ser revisão do Power BI; confira no relatório.
   - Importante: se o relatório tiver **filtros fixos** (por exemplo Motivo Entrada), o resultado pode diferir; me avise.
3. Aba **Actions → "Atualizar painel UMOE" → Run workflow**. Em ~1 minuto a página abre em `https://SEU-USUARIO.github.io/painel-umoe/`. Daí em diante roda sozinho toda hora.

---

## Operação

- **Horário:** o agendador do GitHub pode atrasar de 5 a 30 minutos em horários de pico. O painel mostra o horário real de cada atualização.
- **Falhas:** o GitHub envia e-mail quando uma execução falha. A página anterior continua no ar.
- **Segredo vence em 24 meses:** crie um lembrete no calendário; gere outro segredo e troque em *Secrets*.
- **Inatividade:** o GitHub desliga agendamentos de repositórios sem atividade por 60 dias. O fluxo grava um registro diário (`data/ultima_execucao.txt`) para evitar isso; se um dia receber o aviso do GitHub, é só clicar em *Enable workflow*.
- **Privacidade:** a página é pública para quem tiver o link (igual ao painel atual do Claude), com `noindex` para buscadores. Se precisar de acesso restrito, dá para migrar para Cloudflare Pages + Access ou Azure Static Web Apps.
- **API JSON:** `/api/v1/today.json`, `/api/v1/month.json`, `/api/v1/index.json` na mesma página.

## Rodando localmente (opcional)
```bash
pip install -r requirements.txt
export PBI_TENANT_ID=... PBI_CLIENT_ID=... PBI_CLIENT_SECRET=...
python -m pytest -q                      # testes (não precisam de credenciais)
python -m generator.discover             # lista tabelas/colunas
python -m generator.verify               # confere os totais conhecidos
python -m generator.run --out site       # gera site/index.html e site/api/v1/*.json
```

## Pedido para o TI (copie e cole)

> Preciso de ajuda para automatizar um painel do Power BI. (1) No portal de administração do Power BI → Configurações de locatário: habilitar "Entidades de serviço podem usar APIs do Power BI/Fabric" para o grupo de segurança `painel-umoe-apps`, e habilitar "API REST de Execução de Consultas de Conjunto de Dados". (2) Criar o workspace `UMOE Dashboards` (ou me liberar para criá-lo) e adicionar o grupo `painel-umoe-apps` como Membro. O aplicativo só terá acesso de leitura a esse workspace.

## O que está testado e o que não está
- **Testado (15 testes automáticos):** geração do HTML (idêntico, byte a byte após normalização, ao painel publicado à mão em 08/10/2026), dia vazio, valores negativos, gauge acima da escala, "Demais" por subtração, consultas DAX, abortar quando os números não batem.
- **NÃO testado contra o seu Power BI** (precisa das suas credenciais): os nomes de tabela/colunas e a autenticação. É para isso que existem os passos "Descobrir modelo" e "Verificar valores" — eles provam o mapeamento antes de você confiar no automático.
