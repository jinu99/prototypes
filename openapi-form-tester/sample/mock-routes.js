const express = require("express");
const router = express.Router();

// In-memory store
let nextPetId = 3;
let nextOrderId = 1;

const pets = [
  { id: 1, name: "Buddy", species: "dog", age: 3, vaccinated: true, tags: ["friendly", "trained"] },
  { id: 2, name: "Whiskers", species: "cat", age: 5, vaccinated: false, tags: ["indoor"] },
];

const orders = [];
let settings = { theme: "light", notifications: true, language: "en", maxResults: 20 };

// GET /mock/pets
router.get("/pets", (req, res) => {
  // Intentional drift: include 'createdAt' field not in spec
  const result = pets.map((p) => ({ ...p, createdAt: "2026-01-15T10:00:00Z" }));
  res.json(result);
});

// POST /mock/pets
router.post("/pets", (req, res) => {
  const { name, species, age, vaccinated, tags } = req.body;
  const pet = { id: nextPetId++, name, species, age, vaccinated, tags: tags || [] };
  pets.push(pet);
  res.status(201).json(pet);
});

// GET /mock/pets/:id
router.get("/pets/:id", (req, res) => {
  const pet = pets.find((p) => p.id === parseInt(req.params.id));
  if (!pet) return res.status(404).json({ error: "Pet not found" });
  // Intentional drift: 'vaccinated' returned as string instead of boolean
  res.json({ ...pet, vaccinated: String(pet.vaccinated) });
});

// POST /mock/orders
router.post("/orders", (req, res) => {
  const { petId, quantity, express: isExpress, notes, address } = req.body;
  const order = {
    id: nextOrderId++,
    petId,
    quantity,
    status: "pending",
    express: isExpress,
    notes,
    address,
    // Intentional drift: missing 'status' sometimes isn't noticeable, but 'totalPrice' is undocumented
    totalPrice: quantity * 29.99,
  };
  orders.push(order);
  res.status(201).json(order);
});

// PUT /mock/settings
router.put("/settings", (req, res) => {
  settings = { ...settings, ...req.body };
  // Intentional drift: return 'maxResults' as string instead of integer
  res.json({ ...settings, maxResults: String(settings.maxResults) });
});

module.exports = router;
