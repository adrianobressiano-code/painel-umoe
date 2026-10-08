"""Dados reais de 08/10/2026 (como o Power BI devolve: texto em CAIXA ALTA)."""
from datetime import date
from generator.model import Day

FLEET = [("123052", "COLHEDORA CASE A8810", 9071), ("123061", "COLHEDORA JD CH 670", 7616),
         ("123062", "COLHEDORA JD CH 670", 6198), ("114006", "CM VOLVO VM 270 6X4R", 5381),
         ("102008", "CM VOLVO VM 270 6X4R", 4379), ("122064", "TRATOR CASE PUMA 230", 1835),
         ("123064", "COLHEDORA JD CH 670", 1633), ("102010", "CM VOLKSWAGEN 27.260 6X4", 1590),
         ("153047", "TRANSBORDO TAC 10.500 CIV", 1352), ("180159", "FIAT MOBI LIKE", 900),
         ("159001", "AREA VIV RODOKING CFE 2E", 792), ("180169", "FIAT STRADA ENDURANCE", 335),
         ("123053", "COLHEDORA CASE A8810", 309), ("123058", "COLHEDORA CASE A8810", 280),
         ("122072", "TRATOR CASE PUMA 230", 273), ("180145", "FIAT MOBI LIKE", 259),
         ("153149", "TRANSB TESTON GIGANTE 22T", 89), ("146009", "SULCADOR DMB", 58),
         ("121044", "TRATOR CASE FARMALL 110A", 50), ("103004", "CM VOLVO VM 220 4X2R", 45)]

MATS = [("90574", "BOMBA TRANSMISSAO HIDR (RECOND) CASE 47893387", 1, 9071, "123052", "COLHEDORA CASE A8810"),
        ("105882", "KIT RETENTOR JOHN DEERE CXT40626 / R961003394", 1, 6198, "123062", "COLHEDORA JD CH 670"),
        ("76474", 'DISCO CORTE BASE REVEST 30" 7 FACAS JOHN DEERE/CASE', 3, 4333, "123061", "COLHEDORA JD CH 670"),
        ("78105", "CAIXA CONTROLE VOLVO 84171527", 1, 2932, "114006", "CM VOLVO VM 270 6X4R"),
        ("87241", "ESTIRANTE V VOLVO 22318833", 2, 1993, "102008", "CM VOLVO VM 270 6X4R"),
        ("59777", "CONJUNTO ALAVANCA CASE 48111815/87472289/90512931", 1, 1689, "122064", "TRATOR CASE PUMA 230"),
        ("16151", "BATERIA AUTOMOTIVA 12 VOLTS/100 AMPERES", 2, 1633, "123064", "COLHEDORA JD CH 670"),
        ("105866", "MOTOR PARTIDA 24V VW / PRESTOLITE 23H911023 / 05240", 1, 1590, "102010", "CM VOLKSWAGEN 27.260 6X4"),
        ("44607", "BATENTE MOLEJO VOLVO 20390836", 4, 1519, "102008", "CM VOLVO VM 270 6X4R"),
        ("84855", "COMPRESSOR AR VOLVO 21184142/SANDEN 8044", 1, 1204, "114006", "CM VOLVO VM 270 6X4R")]

MONTH = {"2026-10-01": 56428, "2026-10-02": 266031, "2026-10-03": 15519, "2026-10-04": 0,
         "2026-10-05": 99825, "2026-10-06": 38121, "2026-10-07": 126391, "2026-10-08": 42445}


def day_0810():
    return Day(
        date=date(2026, 10, 8), total=42445,
        classes=[("Manutenção Oportunidade", 11013), ("Manutenção Linear", 9579), ("Manutenção Corretiva", 9039),
                 ("Manutenção Programada", 6198), ("Manutenção Preventiva", 5716), ("Serviço Externo", 900)],
        cost_centers=[("Colhedora Jonh Deere - DE", 24827), ("CAM Comboio - DEMAUT", 5969), ("CAM Diversos - Proprio", 5381),
                      ("TRA Case 205 - DEPREP", 1835), ("Transbordo - DECMEC", 1441), ("Veiculos leves - DEPMAN", 1159),
                      ("Area de vivencia - DECMEC", 792), ("Veiculos leves - DEMAUT", 335), ("Colhedora Case - DECMEC", 280),
                      ("TRA Case 230 - DECMEC", 273), ("Cultivadores - QLOMB", 58), ("TRA Leves e medios - HERB", 50),
                      ("CAM Borracharia - DEMAUT", 45)],
        fleet=FLEET, parts=[("Peças Almoxarifado", 34087), ("Peças Diretas", 8358)],
        materials=[dict(code=a, desc=b, qty=c, value=d, fleet=e, model=f) for a, b, c, d, e, f in MATS])
