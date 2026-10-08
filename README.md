# Painel UMOE — atualização automática, sem seu computador

De hora em hora, 24 horas por dia, o GitHub abre o **link público do seu relatório do Power BI** (o "Publicar na Web"), troca o filtro "Data Aplicação." para o dia de hoje, lê os números, confere se fecham, monta o painel e publica numa página web. **Não precisa de login, de Azure, de administrador do Power BI nem de licença Pro** — só do link que você já tem. Roda de graça no GitHub (Actions + Pages).

```
GitHub Actions (toda hora)
  └─ navegador headless abre o link público do relatório
       └─ fixa a data, lê as tabelas, confere as somas (se não fechar, NÃO publica)
            └─ GitHub Pages:  https://SEU-USUARIO.github.io/painel-umoe/
                              └─ /api/v1/today.json  /month.json  /index.json
```

**Segurança dos números.** Em toda execução: (1) o filtro precisa estar exatamente no dia pedido; (2) classes, centros de custo e tipos de peça precisam somar o total do dia; (3) a frota (o relatório só mostra as 20 maiores) nunca pode passar do total; (4) a soma dos dias do mês precisa bater com o total do período 01→hoje lido no relatório; (5) se algo não bater, a leitura é refeita e, se persistir, **nada é publicado** — a página anterior continua no ar e o GitHub avisa você por e-mail. Todo dia às 02h (Brasília) o mês inteiro é relido, para capturar revisões que o Power BI faça em dias antigos.

---

## Passo a passo (cerca de 20 minutos, uma vez só)

### 1. Conta e repositório no GitHub
1. Crie uma conta grátis em github.com.
2. **New repository** → nome `painel-umoe` → **Public** (necessário para o Pages grátis; o *código* é público, o *link do Power BI* ficará em segredo).
3. **Add file → Upload files** e arraste o conteúdo desta pasta (`generator`, `tests`, `data`, `config.json`, `requirements.txt`, `README*.md`, `.gitignore`).
4. Os agendadores ficam numa pasta oculta (`.github/workflows`) que o navegador costuma não enviar. Crie cada um à mão: **Add file → Create new file**, digite no nome `.github/workflows/atualizar.yml` (o GitHub cria as pastas ao digitar as barras), cole o conteúdo do arquivo de mesmo nome do pacote e clique **Commit**. Repita para `testar-link.yml` (e, se for usar o modo API, `descobrir.yml` e `verificar.yml`).

### 2. Guardar o link do Power BI como segredo
> O link do "Publicar na Web" dá acesso a quem o tiver — por isso **não o cole em nenhum arquivo**, só em *Secrets*.

**Settings → Secrets and variables → Actions → New repository secret**
- Nome: `PBI_PUBLIC_URL`
- Valor: o link `https://app.powerbi.com/view?r=...` completo.

### 3. Ligar o Pages
**Settings → Pages → Build and deployment → Source: GitHub Actions.**

### 4. Testar a leitura (não pule)
1. Aba **Actions → "Testar leitura do link" → Run workflow**.
2. Quando terminar (verde), abra a execução: a linha final mostra algo como  
   `data=2026-10-08 total=R$ 56183 classes=6 centros=19 frota=20 peças=4 materiais=10`.  
   Baixe também o arquivo **diagnostico** (captura de tela + dados lidos) e confira com o relatório.
3. Se ficar vermelho, me mande o texto do erro e a captura de tela.

### 5. Primeira publicação
**Actions → "Atualizar painel UMOE" → Run workflow**, marcando **completo** (lê o mês inteiro, ~4 min). Ao terminar, a página abre em `https://SEU-USUARIO.github.io/painel-umoe/`. Daí em diante roda sozinho toda hora.

Compare com o relatório: o total de hoje, o total do mês (acumulado) e algum dia anterior.

---

## Operação
- **Horário:** o agendador do GitHub pode atrasar de 5 a 30 minutos. O painel mostra a hora real de cada atualização e a hora da base do relatório.
- **Falhas:** o GitHub envia e-mail quando uma execução falha. A página anterior continua no ar.
- **Se desligar o "Publicar na Web"** no Power BI (ou gerar outro link), troque o segredo `PBI_PUBLIC_URL`.
- **Atraso do Power BI:** o "Publicar na Web" costuma refletir o relatório com algum atraso (o relatório mostra a hora da última base, ex.: "08/10/26 18:00"). O painel mostra essa hora no rodapé.
- **Inatividade:** o GitHub desliga agendamentos de repositórios parados por 60 dias; o fluxo grava um registro diário para evitar. Se algum dia chegar o aviso do GitHub, clique em *Enable workflow*.
- **Privacidade:** a página nova é pública para quem tiver o link (como o painel atual do Claude) e tem `noindex`. O link do "Publicar na Web" também é público por natureza — se a empresa não quiser isso, use o caminho oficial (`README_API.md`).
- **Mudou o layout do relatório?** Se alguém renomear colunas/tabelas ou mexer nos visuais, a leitura acusa erro e **não publica**; é só me avisar para ajustar.

## O que está testado e o que não está
- **Testado em 08/10/2026 no seu relatório real** (navegador do seu computador): o link abre sem login, aceita a troca de data, e a leitura devolve exatamente os valores do relatório (07/10 = R$ 126.391; outubro até 08/10 = R$ 658.498; todas as seções somam o total do dia).
- **30 testes automáticos:** interpretação dos números (inclusive negativos e "(Em branco)"), linhas do detalhamento com/sem data de saída, dia vazio, frota parcial, revisão de dias antigos, virada de mês, abortar quando algo não bate, e o HTML gerado idêntico ao painel publicado à mão.
- **Ainda não testado:** a execução dentro do próprio GitHub (o navegador de lá é outro). É para isso o passo 4. Se o GitHub for bloqueado pelo Power BI ou a página se comportar diferente, o passo 4 mostra na hora.

## Rodando no seu computador (opcional)
```bash
pip install -r requirements.txt && python -m playwright install chromium
export PBI_PUBLIC_URL='https://app.powerbi.com/view?r=...'
python -m pytest -q                     # testes
python -m generator.probe               # le o link e mostra o resumo do dia
python -m generator.run --out site --full
```
