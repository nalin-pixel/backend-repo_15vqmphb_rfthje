import os
import random
import base64
from io import BytesIO
from typing import List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ChemBond Tutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Data & Helpers ----------

# Simple knowledge base for common molecules
MOLECULE_DB: Dict[str, Dict[str, Any]] = {
    "H2O": {
        "name": "Water",
        "bond_type": "Polar covalent",
        "bond_angle": 104.5,
        "single_bonds": 2,
        "double_bonds": 0,
        "shape": "Bent (V-shaped)",
        "lewis": "H–O–H with two lone pairs on oxygen",
        "lewis_text": "Lewis Structure of H2O: Oxygen in the center with two single bonds to H and two lone pairs on O.",
        "explanation": "Oxygen forms two polar covalent bonds with hydrogen. Lone pairs on O push bonds, giving a bent shape and polarity.",
        "lewis_ascii": "H :O: H\n   .. ..",
    },
    "CO2": {
        "name": "Carbon dioxide",
        "bond_type": "Non‑polar covalent (double bonds)",
        "bond_angle": 180.0,
        "single_bonds": 0,
        "double_bonds": 2,
        "shape": "Linear",
        "lewis": "O=C=O",
        "lewis_text": "Lewis Structure of CO2: Carbon in center with double bonds to two oxygens (O=C=O).",
        "explanation": "Two equal C=O bonds arranged linearly cancel dipoles, so the molecule is non‑polar.",
        "lewis_ascii": "O = C = O",
    },
    "CH4": {
        "name": "Methane",
        "bond_type": "Non‑polar covalent",
        "bond_angle": 109.5,
        "single_bonds": 4,
        "double_bonds": 0,
        "shape": "Tetrahedral",
        "lewis": "Carbon in center with four single bonds to H",
        "lewis_text": "Lewis Structure of CH4: Carbon in center with four single bonds to hydrogens (tetrahedral).",
        "explanation": "Four equivalent C–H bonds arranged tetrahedrally make CH4 non‑polar overall.",
        "lewis_ascii": "    H\n    |\nH — C — H\n    |\n    H",
    },
    "NH3": {
        "name": "Ammonia",
        "bond_type": "Polar covalent",
        "bond_angle": 107.0,
        "single_bonds": 3,
        "double_bonds": 0,
        "shape": "Trigonal pyramidal",
        "lewis": "N with three single bonds to H and one lone pair",
        "lewis_text": "Lewis Structure of NH3: Nitrogen in center with three single bonds to H and one lone pair on N.",
        "explanation": "Lone pair on nitrogen compresses H–N–H angles; N–H bonds are polar making NH3 polar.",
        "lewis_ascii": "   H\n   |\nH–N: \n   |\n   H",
    },
    "NaCl": {
        "name": "Sodium chloride",
        "bond_type": "Ionic",
        "bond_angle": None,
        "single_bonds": 0,
        "double_bonds": 0,
        "shape": "Ionic lattice (not molecular)",
        "lewis": "Na+ and Cl− ions",
        "lewis_text": "Lewis Structure of NaCl: Na donates one electron to Cl forming Na+ and Cl−; ionic lattice in solid.",
        "explanation": "Metal (Na) transfers an electron to nonmetal (Cl), forming oppositely charged ions that attract.",
        "lewis_ascii": "[Na]+  :Cl:−",
    },
    "HF": {
        "name": "Hydrogen fluoride",
        "bond_type": "Polar covalent with strong hydrogen bonding between molecules",
        "bond_angle": None,
        "single_bonds": 1,
        "double_bonds": 0,
        "shape": "Diatomic",
        "lewis": "H–F with three lone pairs on F",
        "lewis_text": "Lewis Structure of HF: Single bond H–F with three lone pairs on F.",
        "explanation": "Large electronegativity difference makes the bond highly polar.",
        "lewis_ascii": "H–F:::",
    },
    "O2": {
        "name": "Oxygen",
        "bond_type": "Non‑polar covalent (double bond)",
        "bond_angle": None,
        "single_bonds": 0,
        "double_bonds": 1,
        "shape": "Diatomic",
        "lewis": "O=O",
        "lewis_text": "Lewis Structure of O2: Double bond between two oxygens.",
        "explanation": "Two identical atoms share electrons equally.",
        "lewis_ascii": "O = O",
    },
    "N2": {
        "name": "Nitrogen",
        "bond_type": "Non‑polar covalent (triple bond)",
        "bond_angle": None,
        "single_bonds": 0,
        "double_bonds": 0,
        "shape": "Diatomic",
        "lewis": "N≡N",
        "lewis_text": "Lewis Structure of N2: Triple bond between two nitrogens.",
        "explanation": "Two identical atoms share three pairs of electrons equally.",
        "lewis_ascii": "N ≡ N",
    },
    "SO2": {
        "name": "Sulfur dioxide",
        "bond_type": "Polar covalent (resonance; average bond order >1)",
        "bond_angle": 119.0,
        "single_bonds": 0,
        "double_bonds": 2,
        "shape": "Bent",
        "lewis": "O=S=O (resonance forms)",
        "lewis_text": "Lewis Structure of SO2: Bent molecule with resonance between S=O bonds.",
        "explanation": "Electron domains around S make a bent shape; polar due to asymmetry.",
        "lewis_ascii": "O = S = O",
    },
}


def normalize_formula(s: str) -> str:
    return s.replace(" ", "").replace("·", ".").upper()


def make_lewis_svg(formula: str, ascii_diagram: str) -> str:
    """Return a data:image/svg+xml;base64 URI of a simple Lewis diagram.
    We render monospaced ASCII art into an SVG for portability.
    """
    lines = ascii_diagram.split("\n")
    line_height = 22
    padding = 16
    width = max(len(line) for line in lines) * 12 + padding * 2
    height = len(lines) * line_height + padding * 2
    # Escape XML special chars
    def esc(t: str) -> str:
        return (t.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))

    text_elems = []
    for i, line in enumerate(lines):
        y = padding + (i + 1) * line_height
        text_elems.append(f"<text x='{padding}' y='{y}' font-family='IBM Plex Mono, monospace' font-size='18'>{esc(line)}</text>")
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>
      <rect x='0' y='0' width='{width}' height='{height}' fill='white' stroke='#e5e7eb'/>
      {''.join(text_elems)}
    </svg>
    """.strip()
    data = svg.encode("utf-8")
    uri = "data:image/svg+xml;base64," + base64.b64encode(data).decode("utf-8")
    return uri


# ---------- Schemas ----------

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

class QuizRequest(BaseModel):
    topic: str
    count: int = 5

class QuizItem(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str

class QuizResponse(BaseModel):
    items: List[QuizItem]

class MoleculeRequest(BaseModel):
    formula: str

class MoleculeAnalysis(BaseModel):
    formula: str
    name: str | None
    bond_type: str
    bond_angle: float | None
    single_bonds: int
    double_bonds: int
    shape: str | None
    explanation: str
    lewis_text: str
    lewis_ascii: str
    lewis_svg: str


# ---------- Endpoints ----------

@app.get("/")
def read_root():
    return {"message": "ChemBond Tutor API is running"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    q = req.message.strip().lower()
    # Pre-baked explanations
    concepts = {
        "ionic": "Ionic bonding happens when a metal transfers electrons to a nonmetal, forming oppositely charged ions that attract. Example: NaCl (sodium chloride).",
        "covalent": "Covalent bonding is when two nonmetals share electron pairs to fill their outer shells. Example: H2 (hydrogen), CH4 (methane).",
        "metallic": "Metallic bonding is a lattice of positive metal ions immersed in a 'sea' of delocalized electrons. This explains metals' conductivity and malleability.",
        "coordinate": "A coordinate (dative) covalent bond is a covalent bond where both shared electrons come from the same atom. Example: NH4+ forms when NH3 donates a lone pair to H+.",
        "hydrogen": "Hydrogen bonding is a strong dipole–dipole attraction between H attached to O, N, or F and a lone pair on a neighboring O, N, or F. Example: water molecules hydrogen-bond to each other.",
        "vsepr": "VSEPR theory predicts 3D shapes using electron pair repulsions: electron domains arrange to minimize repulsion (e.g., linear 180°, trigonal planar 120°, tetrahedral 109.5°).",
    }
    # Molecule-specific answers
    for key, data in MOLECULE_DB.items():
        if key.lower() in q or (data.get("name","" ).lower() in q):
            reply = (
                f"Molecule: {key}\n"
                f"Type of Bond: {data['bond_type']}\n"
                f"Bond Angle: {data['bond_angle']}°" if data['bond_angle'] is not None else "Bond Angle: Not applicable for diatomic/ionic lattice"
            )
            extra = f"\nExplanation: {data['explanation']}"
            return {"reply": reply + extra}

    for term, desc in concepts.items():
        if term in q:
            return {"reply": desc}

    # General fallbacks
    if "what is" in q or "explain" in q or "define" in q:
        return {"reply": "I can help with bonding concepts (ionic, covalent, metallic, coordinate, hydrogen) and common molecules like H2O, CO2, CH4, NH3, and NaCl. Ask: 'Explain ionic bonding' or 'Why is H2O polar?'"}

    return {"reply": "Great question! Could you specify the concept (e.g., ionic bonding) or a molecule (e.g., H2O) you want to learn about?"}


QUIZ_BANK: Dict[str, List[Dict[str, Any]]] = {
    "Ionic Bonding": [
        {
            "q": "Which type of bond is formed between sodium and chlorine?",
            "options": ["Ionic", "Covalent", "Metallic", "Hydrogen"],
            "a": 0,
            "e": "Na (metal) transfers an electron to Cl (nonmetal) forming ions."
        },
        {
            "q": "What holds ions together in an ionic compound?",
            "options": ["Electrostatic attraction", "Electron sharing", "Magnetic forces", "Hydrogen bonds"],
            "a": 0,
            "e": "Oppositely charged ions attract strongly."
        },
    ],
    "Covalent Bonding": [
        {
            "q": "Which type of elements typically form covalent bonds?",
            "options": ["Two nonmetals", "Metal and nonmetal", "Two metals", "Metal and metalloid"],
            "a": 0,
            "e": "Covalent bonds usually form between nonmetals sharing electrons."
        },
        {
            "q": "In CO2, what type of bonds connect C and O?",
            "options": ["Double covalent", "Single covalent", "Ionic", "Metallic"],
            "a": 0,
            "e": "Each oxygen shares two electrons with carbon (O=C=O)."
        },
    ],
    "VSEPR Theory": [
        {
            "q": "Ideal bond angle in a tetrahedral geometry is…",
            "options": ["109.5°", "180°", "120°", "90°"],
            "a": 0,
            "e": "Tetrahedral electron domain geometry gives 109.5°."
        },
        {
            "q": "The shape of CO2 according to VSEPR is…",
            "options": ["Linear", "Bent", "Trigonal pyramidal", "Tetrahedral"],
            "a": 0,
            "e": "Two electron domains around carbon → linear."
        },
    ],
}

@app.post("/api/quiz", response_model=QuizResponse)
def generate_quiz(req: QuizRequest):
    topic = req.topic.strip()
    count = max(1, min(10, req.count or 5))
    bank = QUIZ_BANK.get(topic)
    if not bank:
        # default simple quiz if topic not found
        bank = [
            {"q": f"Basic question on {topic}: Covalent bonds are formed by…",
             "options": ["Sharing electrons", "Transferring electrons", "Sharing protons", "Magnetic forces"],
             "a": 0,
             "e": "Covalent = sharing of electron pairs."},
            {"q": "Ionic bonds usually form between…",
             "options": ["Metals and nonmetals", "Two nonmetals", "Two metals", "Noble gases"],
             "a": 0,
             "e": "Metal + nonmetal → electron transfer."},
        ]
    # Expand by repeating and small variations if needed
    pool = bank * ((count + len(bank) - 1) // len(bank))
    random.shuffle(pool)
    items: List[QuizItem] = []
    for item in pool[:count]:
        options = item["options"][:]
        correct_text = options[item["a"]]
        random.shuffle(options)
        correct_index = options.index(correct_text)
        items.append(QuizItem(question=item["q"], options=options, correct_index=correct_index, explanation=item["e"]))
    return {"items": items}


@app.post("/api/molecule/analyze", response_model=MoleculeAnalysis)
def analyze_molecule(req: MoleculeRequest):
    f = normalize_formula(req.formula)
    data = MOLECULE_DB.get(f)
    if not data:
        # Heuristic fallback: very simple guesses
        guess = {
            "bond_type": "Covalent (heuristic)",
            "bond_angle": None,
            "single_bonds": 0,
            "double_bonds": 0,
            "shape": None,
            "lewis": f"Lewis structure depends on valence counts for {f}.",
            "lewis_text": f"Lewis structure for {f} is not in the quick database. Try H2O, CO2, CH4, NH3, or NaCl.",
            "explanation": "This is a generic estimate. For exact details, try a common molecule from the examples.",
            "lewis_ascii": f"{f}",
        }
        svg = make_lewis_svg(f, guess["lewis_ascii"])
        return MoleculeAnalysis(
            formula=f,
            name=None,
            bond_type=guess["bond_type"],
            bond_angle=guess["bond_angle"],
            single_bonds=guess["single_bonds"],
            double_bonds=guess["double_bonds"],
            shape=guess["shape"],
            explanation=guess["explanation"],
            lewis_text=guess["lewis_text"],
            lewis_ascii=guess["lewis_ascii"],
            lewis_svg=svg,
        )

    svg = make_lewis_svg(f, data.get("lewis_ascii", data.get("lewis", f)))
    return MoleculeAnalysis(
        formula=f,
        name=data.get("name"),
        bond_type=data.get("bond_type"),
        bond_angle=data.get("bond_angle"),
        single_bonds=data.get("single_bonds", 0),
        double_bonds=data.get("double_bonds", 0),
        shape=data.get("shape"),
        explanation=data.get("explanation"),
        lewis_text=data.get("lewis_text", data.get("lewis", "")),
        lewis_ascii=data.get("lewis_ascii", data.get("lewis", "")),
        lewis_svg=svg,
    )


@app.get("/test")
def test_database():
    """Health check (also shows DB env if present)."""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Used",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
    }
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
