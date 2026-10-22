# -*- coding: utf-8 -*-
import json

# Mapa de dados de 2025 extraido da planilha oficial (Codigo -> {correspondencia, pergunta_2025, resposta_2025})
dados_2025 = {
    "I.1.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "1) A Secretaria realiza ações integradas e intersetoriais na implementação da política de alfabetização?\n2) A Secretaria realiza ações de fortalecimento da intersetorialidade na implementação de políticas de Educação em Tempo Integral?",
        "resposta_2025": "1) Sim.\n2) Sim."
    },
    "I.2.2": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria dispõe de estrutura própria para apoio à gestão das escolas (ex.: Núcleo de Apoio às Escolas)?",
        "resposta_2025": "Sim."
    },
    "I.2.4": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria possui ações para a superação do abandono e da evasão dos estudantes das escolas, em todas as etapas e modalidades de ensino ofertadas?",
        "resposta_2025": "Sim."
    },
    "I.2.5": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria incentiva a colaboração e o compartilhamento de práticas e experiências entre os gestores escolares?",
        "resposta_2025": "Sim."
    },
    "I.3.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "1) A Secretaria de Educação possui algum protocolo para casos de racismo ou injúria racial?\n2) A Secretaria de Educação orienta as escolas a implementarem os protocolos de combate ao racismo nas escolas?",
        "resposta_2025": "1) Sim.\n2) Sim."
    },
    "I.3.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Quantos Territórios Etnoeducacionais (TEEs) existem no seu município (ou estado/Distrito Federal)?",
        "resposta_2025": "2"
    },
    "I.4.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A estrutura administrativa da Secretaria de Educação está aprovada em legislação?",
        "resposta_2025": "Sim."
    },
    "I.5.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "Em que estágio se encontra o processo de elaboração ou revisão da política estadual de Educação em Tempo Integral pela Secretaria?",
        "resposta_2025": "Em elaboração."
    },
    "I.5.2": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "O estado ou o município possui lei, norma ou portaria própria sobre a ampliação de matrícula em tempo integral?",
        "resposta_2025": "Sim."
    },
    "I.6.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A sua rede possui carreira para os profissionais do magistério?",
        "resposta_2025": "Sim."
    },
    "I.6.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria possui equipe técnica responsável pelo planejamento e implementação da política de tecnologia e inovação pedagógica na rede?",
        "resposta_2025": "Sim."
    },
    "I.6.3": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria realiza avaliação de desempenho dos diretores escolares?",
        "resposta_2025": "Não possui."
    },
    "I.6.4": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "Qual é o percentual de docentes que possuem mais de um vínculo público na sua rede de ensino?",
        "resposta_2025": "2"
    },
    "I.6.5": {
        "correspondencia": "Igual",
        "pergunta_2025": "1) Todos os docentes concursados usufruem da reserva de um terço da jornada em hora-atividade?\n2) O município ou o estado possui normativo que viabilize que um terço da carga horária dos professores seja destinada para planejamento pedagógico e formação?",
        "resposta_2025": "1) Sim.\n2) Sim."
    },
    "I.6.6": {
        "correspondencia": "Igual",
        "pergunta_2025": "Todos os docentes contratados usufruem da reserva de um terço da jornada em hora-atividade?",
        "resposta_2025": "Sim."
    },
    "I.6.7": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "1) Como a Secretaria de Educação organiza o processo de contratação temporária de professores e demais profissionais da Educação?\n2) Existe legislação específica para contratação temporária de professores e demais profissionais da Educação?",
        "resposta_2025": "1) Processo Seletivo Amplo (com aplicação de prova – teórica e/ou prática – e análise de currículo e experiência profissional).\n2) Sim."
    },
    "I.6.8": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "Como a Secretaria de Educação organiza o processo de contratação temporária de professores e demais profissionais da Educação?",
        "resposta_2025": "Processo Seletivo Amplo (com aplicação de prova – teórica e/ou prática – e análise de currículo e experiência profissional)."
    },
    "I.6.9": {
        "correspondencia": "Igual",
        "pergunta_2025": "Em quais das seguintes áreas a gestão municipal/estadual conta com corpo técnico permanente?",
        "resposta_2025": "Pedagógica; Orçamentária-financeira; Gestão de Pessoas; Alimentação Escolar; Transporte; Convênios e captação de recursos; Licitação e contratos; Obras; Jurídico."
    },
    "I.7.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "Para quais temas a Secretaria utiliza sistemas informatizados de gestão?",
        "resposta_2025": "Processos administrativos eletrônicos; Gestão Orçamentária; Gestão Financeira; Gestão de Pessoas; Gestão de Patrimônio; Gestão do transporte escolar; Gestão da alimentação escolar."
    },
    "I.7.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Para quais temas da gestão escolar a Secretaria dispõe de sistemas informatizados de gestão?",
        "resposta_2025": "Matrícula e enturmação de estudantes; Alocação de professores às turmas; Lançamento e gestão de notas; Controle de frequência."
    },
    "I.7.3": {
        "correspondencia": "Igual",
        "pergunta_2025": "Dentre os sistemas de informação indicados nas perguntas anteriores, como a Secretaria adquiriu ou obteve esses sistemas?",
        "resposta_2025": "A maioria é desenvolvida por fontes diversas (combinação de esforços internos, externos e colaboração)."
    },
    "I.7.4": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual é o nível de implantação de sistemas de gestão e informação nas escolas da rede?",
        "resposta_2025": "Alto. Todas as escolas utilizam sistemas de informação e gestão."
    },
    "I.7.5": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual é o nível de integração/interoperabilidade dos sistemas da Secretaria?",
        "resposta_2025": "Há alto grau de integração/interoperabilidade entre os sistemas da Secretaria e com sistemas externos, por meio de APIs."
    },
    "I.7.6": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "Como são realizados os processos de coleta e armazenamento de dados?",
        "resposta_2025": "A coleta de dados pela Secretaria é realizada com o apoio de sistemas informatizados e, a depender da necessidade, a Secretaria também conta com ferramentas de integração e coleta de dados (ex.: API). O armazenamento desses dados é feito em bancos de dados da Secretaria, de forma consolidada."
    },
    "I.8.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A equipe da Secretaria de Educação elabora os programas e as ações que integrarão o Plano Plurianual e a Lei de Diretrizes Orçamentárias?",
        "resposta_2025": "Sim."
    },
    "I.8.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual(is) etapas da execução orçamentária de recursos da educação está(ão) sob a responsabilidade da Secretaria de Educação?",
        "resposta_2025": "Empenho; Liquidação; Pagamento."
    },
    "I.8.3": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria da Educação conta, em sua equipe, com pessoal técnico dotado de conhecimento sobre planejamento e execução orçamentária?",
        "resposta_2025": "Sim."
    },
    "I.8.4": {
        "correspondencia": "Igual",
        "pergunta_2025": "Quem realiza o registro de informações junto ao Siope?",
        "resposta_2025": "Outros profissionais da Secretaria de Educação."
    },
    "I.8.5": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria de Educação realiza, com regularidade, o controle de quais receitas?",
        "resposta_2025": "Fundeb; 25% destinado à MDE (Art. 212 da CF); Salário-Educação; PNAE; PNATE; PDDE; PAR; Recursos transferidos pelo governo do estado (ex.: transporte escolar); Outras transferências do FNDE."
    },
    "I.8.6": {
        "correspondencia": "Igual",
        "pergunta_2025": "O estado ou o município possui Fundo de Educação instituído por lei?",
        "resposta_2025": "Sim."
    },
    "I.9.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria realiza supervisão pedagógica das suas escolas?",
        "resposta_2025": "Sim."
    },
    "I.10.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "1) A Secretaria planeja a alocação de matrículas em tempo integral, buscando garantir a equidade, especialmente para os estudantes em situação de vulnerabilidade social?\n2) A Secretaria possui equipe técnica responsável pela expansão e gestão das matrículas de tempo integral na rede?",
        "resposta_2025": "1) Sim.\n2) Sim."
    },
    "I.10.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Há, no seu território, demanda por Educação de Jovens e Adultos (EJA) não atendida?",
        "resposta_2025": "Não possui."
    },
    "I.10.3": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria considera, ao ofertar Educação de Jovens e Adultos (EJA), as especificidades de estudantes em situação de vulnerabilidade social?",
        "resposta_2025": "Sim."
    },
    "I.10.4": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria tem adotado medidas de reordenamento das matrículas na rede, com fechamento de escolas?",
        "resposta_2025": "Sim."
    },
    "I.10.5": {
        "correspondencia": "Igual",
        "pergunta_2025": "Se sim, em que tipo de escolas?",
        "resposta_2025": "Campo; Urbanas."
    },
    "I.11.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria Estadual de Educação atua em regime de colaboração com os municípios para garantir a conectividade das escolas, expandir a oferta de tecnologias digitais na Educação Básica e/ou garantir a inclusão da Educação Digital no currículo?",
        "resposta_2025": "Não se aplica."
    },
    "I.11.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "O estado ou o município faz parte, atualmente, de algum consórcio público com atuação na área da Educação ou Arranjo de Desenvolvimento da Educação (ADE)?",
        "resposta_2025": "Não possui."
    },
    "I.11.3": {
        "correspondencia": "Igual",
        "pergunta_2025": "Se sim, quais são as áreas de atuação do Consórcio e/ou ADE?",
        "resposta_2025": "Não se aplica."
    },
    "I.12.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "Existe algum protocolo de adaptação e resiliência às mudanças climáticas para atuação pelas equipes escolares?",
        "resposta_2025": "Não possui."
    },
    "II.1.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria possui um plano de formação estruturado para diretores escolares e coordenadores pedagógicos?",
        "resposta_2025": "Sim, para ambos."
    },
    "II.1.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual é o percentual de profissionais da Secretaria de Educação (órgão central) ou das Regionais de Ensino que participaram de formações continuadas no último ano?",
        "resposta_2025": "48"
    },
    "II.1.3": {
        "correspondencia": "Igual",
        "pergunta_2025": "No último ano, houve oferta de formação continuada, com duração mínima de 40 horas, para quais profissionais da rede?",
        "resposta_2025": "Professores; Auxiliares de professores; Diretores escolares; Coordenadores pedagógicos; Outros profissionais das escolas; Equipe técnica das Regionais de Ensino; Equipe técnica da Secretaria."
    },
    "II.1.4": {
        "correspondencia": "Igual",
        "pergunta_2025": "Em quais formatos a Secretaria costuma oferecer formação continuada?",
        "resposta_2025": "Presencial; A distância; Híbrido."
    },
    "II.1.5": {
        "correspondencia": "Igual",
        "pergunta_2025": "De que forma a Secretaria costuma oferecer formação continuada?",
        "resposta_2025": "Iniciativa própria; Parceria."
    },
    "II.1.6": {
        "correspondencia": "Igual",
        "pergunta_2025": "No último ano, houve oferta de formação continuada de, no mínimo, 40 horas para os profissionais de quais etapas de ensino da Educação Básica?",
        "resposta_2025": "Educação Infantil; EF Anos Iniciais (1º e 2º anos); EF Anos Iniciais (3º ao 5º ano); EF Anos Finais (6º ao 9º ano); Ensino Médio."
    },
    "II.1.7": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual é o percentual de profissionais da Educação Escolar Quilombola (gestores e professores) com formação específica?",
        "resposta_2025": "0"
    },
    "II.1.8": {
        "correspondencia": "Igual",
        "pergunta_2025": "A rede possui quantidade suficiente de professores bilíngues, com formação e especialização adequadas, para atender os estudantes surdos, surdocegos, com deficiência auditiva sinalizante, surdos com altas habilidades ou superdotação ou com deficiências?",
        "resposta_2025": "Sim, parcialmente."
    },
    "II.2.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria oferece, para a sua equipe técnica, formação em políticas de Educação em Tempo Integral?",
        "resposta_2025": "Sim."
    },
    "III.1.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria Estadual de Educação promove, anualmente, avaliação da alfabetização para os estudantes das redes municipais (e da rede estadual, se for o caso), no 2º ano do Ensino Fundamental?",
        "resposta_2025": "Sim."
    },
    "III.1.3": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria Estadual de Educação promove, anualmente, avaliações de Língua Portuguesa e de Matemática?",
        "resposta_2025": "Sim."
    },
    "III.1.4": {
        "correspondencia": "Igual",
        "pergunta_2025": "Se sim, em quais séries?",
        "resposta_2025": "5º ano do Ensino Fundamental; 9º ano do Ensino Fundamental; 3ª série do Ensino Médio."
    },
    "III.1.5": {
        "correspondencia": "Igual",
        "pergunta_2025": "Se sim, quais escolas participam da avaliação?",
        "resposta_2025": "Rede pública estadual."
    },
    "III.2.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria possui orientações curriculares referentes ao processo de alfabetização, contemplando métodos pedagógicos diversificados, de modo a garantir que todas as crianças sejam alfabetizadas?",
        "resposta_2025": "Sim."
    },
    "III.2.2": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria possui currículo específico para as escolas em tempo integral?",
        "resposta_2025": "Sim."
    },
    "III.2.5": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "Os objetivos de aprendizagem, as competências e as habilidades da BNCC Computação foram incorporados ao currículo da rede de ensino?",
        "resposta_2025": "Parcialmente, em algumas etapas de ensino."
    },
    "IV.1.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A Secretaria dispõe de veículos (caminhões frigoríficos) apropriados para o transporte de alimentos?",
        "resposta_2025": "Não possui."
    },
    "IV.1.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Na composição do cardápio nutricional, a Secretaria considera e incorpora as tradições de culinária e de cultura alimentar das comunidades às quais pertencem os estudantes, integrando a promoção e o fortalecimento da agricultura familiar local?",
        "resposta_2025": "Sim."
    },
    "IV.1.3": {
        "correspondencia": "Igual",
        "pergunta_2025": "O cardápio da alimentação escolar é preparado priorizando os alimentos in natura e minimamente processados e limitando a oferta de processados e ultraprocessados, considerando a necessária qualidade e variedade?",
        "resposta_2025": "Sim."
    },
    "IV.1.4": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual é o percentual de escolas que possuem horta implementada/utilizada como espaço pedagógico?",
        "resposta_2025": "10"
    },
    "IV.1.6": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual é o percentual de escolas de Educação Infantil com sala de apoio à amamentação?",
        "resposta_2025": "47"
    },
    "IV.1.7": {
        "correspondencia": "Igual",
        "pergunta_2025": "Qual é o percentual de escolas de Educação Infantil com equipamentos e instalações adequados para armazenamento, manipulação e oferta do leite materno, durante a permanência dos bebês nos estabelecimentos?",
        "resposta_2025": "100"
    },
    "IV.2.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "1) A Secretaria de Educação ou outro órgão do governo estadual (ou Distrito Federal) contrata, de forma centralizada, serviço de conexão à internet para as escolas da rede?\n2) A Secretaria de Educação ou outro órgão do governo estadual (ou Distrito Federal) contrata, de forma centralizada, serviço de Wi-Fi para as escolas?",
        "resposta_2025": "1) Sim.\n2) Não possui."
    },
    "IV.2.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Há espaço dedicado à formação e experimentação de tecnologias digitais para professores, onde eles podem desenvolver habilidades práticas e teóricas na utilização de tecnologias na prática pedagógica?",
        "resposta_2025": "Sim."
    },
    "IV.3.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "Existem materiais didáticos em quantidade suficiente para promover o uso de métodos pedagógicos diversos para atender aos objetivos do Compromisso Nacional Criança Alfabetizada?",
        "resposta_2025": "Não possui."
    },
    "IV.3.2": {
        "correspondencia": "Igual",
        "pergunta_2025": "Há recursos pedagógicos suficientes para a implementação dos programas de alfabetização da rede?",
        "resposta_2025": "Não possui."
    },
    "IV.3.3": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria oferece material didático para as escolas implementarem o currículo de Educação Digital nos eixos de Cultura Digital, Mundo Digital e Pensamento Computacional, conforme previsto na BNCC Computação e na Política Nacional de Educação Digital?",
        "resposta_2025": "Não possui."
    },
    "IV.3.4": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria possui e/ou disponibiliza, para o uso das escolas, recursos educacionais digitais (ex.: plataforma educacional, repositório digital, ambiente virtual de aprendizagem etc.)?",
        "resposta_2025": "Sim."
    },
    "IV.3.5": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A rede de ensino adquiriu equipamentos e dispositivos eletrônicos (ex.: notebooks, desktops, Chromebooks) para o uso pedagógico dos docentes e de estudantes das escolas da rede, nos últimos 24 meses?",
        "resposta_2025": "Sim."
    },
    "IV.3.6": {
        "correspondencia": "Igual",
        "pergunta_2025": "1) A Secretaria de Educação faz a aquisição de materiais didático-pedagógicos que respeitem e promovam a diversidade étnico-racial, tais como: filmes, jogos, livros ou brinquedos?\n2) Se sim, indique para qual(is) etapa(s):",
        "resposta_2025": "1) Sim.\n2) Educação Infantil; Ensino Fundamental (1º ao 5º ano); Ensino Fundamental (6º ao 9º ano); Ensino Médio."
    },
    "IV.4.1": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "1) A Secretaria disponibiliza transporte escolar aos estudantes?\n2) Se sim, especifique quais meios de transporte a Secretaria utiliza/disponibiliza:",
        "resposta_2025": "1) Sim.\n2) Ônibus próprios; Ônibus terceirizados."
    },
    "IV.4.2": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "Se sim, especifique quais meios de transporte a Secretaria utiliza/disponibiliza:",
        "resposta_2025": "Ônibus próprios; Ônibus terceirizados."
    },
    "IV.4.3": {
        "correspondencia": "Semelhante",
        "pergunta_2025": "A disponibilidade do transporte escolar é suficiente para atender à demanda dos educandos da rede pública?",
        "resposta_2025": "Não possui."
    },
    "IV.5.1": {
        "correspondencia": "Igual",
        "pergunta_2025": "A Secretaria dispõe de veículos para apoio às necessidades administrativas?",
        "resposta_2025": "Sim."
    }
}

with open("questions_data.json", "r", encoding="utf-8") as f:
    qs = json.load(f)

count_2025 = 0
for q in qs:
    cod = q["codigo"]
    if cod in dados_2025:
        q["tem_2025"] = True
        q["correspondencia_2025"] = dados_2025[cod]["correspondencia"]
        q["pergunta_2025"] = dados_2025[cod]["pergunta_2025"]
        q["resposta_2025"] = dados_2025[cod]["resposta_2025"]
        count_2025 += 1
    else:
        q["tem_2025"] = False
        q["correspondencia_2025"] = "Nova em 2026"
        q["pergunta_2025"] = ""
        q["resposta_2025"] = ""

with open("questions_data.json", "w", encoding="utf-8") as f:
    json.dump(qs, f, ensure_ascii=False, indent=2)

print(f"Atualizadas {len(qs)} questoes, das quais {count_2025} possuem historico de 2025!")
