const EXAMPLE_RESULTS = {
  "schema_version": 1,
  "release": "September 2026 pilot",
  "dataset_sha256": "b841b82c169c0721b97dd254c992072b0ccc1c8e11d74ce61fc7a9c7aedce363",
  "examples": {
    "attachment": [
      {
        "model": "openai/gpt-6-astra",
        "name": "GPT-6 Astra",
        "score": 1.0,
        "status": "correct",
        "answer": "3397",
        "note": "Identified 3397, the lower control arm."
      },
      {
        "model": "anthropic/claude-fable-5.1",
        "name": "Claude Fable 5.1",
        "score": 0.0,
        "status": "incorrect",
        "answer": "3078",
        "note": "Answered 3078 instead of 3397 (lower control arm)."
      },
      {
        "model": "openai/gpt-5.6-sol-pro",
        "name": "GPT-5.6 Sol Pro",
        "score": 0.0,
        "status": "incorrect",
        "answer": "3078",
        "note": "Answered 3078 instead of 3397 (lower control arm)."
      },
      {
        "model": "google/gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "score": 0.0,
        "status": "incorrect",
        "answer": "3078",
        "note": "Answered 3078 instead of 3397 (lower control arm)."
      },
      {
        "model": "x-ai/grok-4.6",
        "name": "Grok 4.6",
        "score": 0.0,
        "status": "incorrect",
        "answer": "3105",
        "note": "Answered 3105 instead of 3397 (lower control arm)."
      },
      {
        "model": "qwen/qwen3.8-max-0902",
        "name": "Qwen 3.8 Max 0902",
        "score": 0.0,
        "status": "incomplete",
        "answer": null,
        "note": "The provider returned an error with no final answer. Scored zero; this does not establish what the model would have answered."
      },
      {
        "model": "z-ai/glm-5.3-flash",
        "name": "GLM 5.3 Flash",
        "score": 0.0,
        "status": "incomplete",
        "answer": null,
        "note": "Reached the 32,768-token output limit without a complete final answer. Scored zero; there is no completed answer to compare."
      },
      {
        "model": "qwen/qwen3.8-flash",
        "name": "Qwen 3.8 Flash",
        "score": 0.0,
        "status": "incorrect",
        "answer": "3078",
        "note": "Answered 3078 instead of 3397 (lower control arm)."
      },
      {
        "model": "bytedance-seed/seed-2-1-turbo",
        "name": "Seed 2.1 Turbo",
        "score": 0.0,
        "status": "incomplete",
        "answer": null,
        "note": "Reached the 32,768-token output limit without a complete final answer. Scored zero; there is no completed answer to compare."
      },
      {
        "model": "deepseek/deepseek-v4-flash-vision-exp",
        "name": "DeepSeek V4 Vision Exp",
        "score": 0.0,
        "status": "incorrect",
        "answer": "3A097",
        "note": "Answered 3A097 instead of 3397 (lower control arm)."
      }
    ],
    "hardware": [
      {
        "model": "openai/gpt-6-astra",
        "name": "GPT-6 Astra",
        "score": 1.0,
        "status": "correct",
        "answer": "From 3-1-66, the attachment nut for 18A017 changed from 33923-S to 34392-S, and the attachment bolt changed from 355471-S to 378940-S.",
        "note": "Identified both the nut replacement and the bolt replacement correctly."
      },
      {
        "model": "anthropic/claude-fable-5.1",
        "name": "Claude Fable 5.1",
        "score": 1.0,
        "status": "correct",
        "answer": "The diagram shows a dated hardware change (effective 3-1-66) for the 18A017 shock absorber upper bracket attachment: the nut changed from 33923-S (before 3-1-66) to 34392-S (from 3-1-66), and the bolt changed from 355471-S (before 3-1-66) to 378940-S (from 3-1-66).",
        "note": "Identified both replacements correctly, including the changeover date."
      },
      {
        "model": "openai/gpt-5.6-sol-pro",
        "name": "GPT-5.6 Sol Pro",
        "score": 0.5,
        "status": "partial",
        "answer": "Effective 3-1-66, the attachment nut for 18A017 changed from 33923-S to 34392-S.",
        "note": "Identified the nut change but omitted the bolt change from 355471-S to 378940-S. Earned half credit."
      },
      {
        "model": "google/gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "score": 1.0,
        "status": "correct",
        "answer": "Effective 3-1-66, the attachment hardware for bracket 18A017 changed as follows:\n- The mounting nut changed from 33923-S ('BEFORE 3-1-66') to 34392-S ('FROM 3-1-66').\n- The mounting bolt changed from 355471-S ('BEFORE 3-1-66') to 378940-S ('FROM 3-1-66').",
        "note": "Identified both replacements correctly, including the changeover date."
      },
      {
        "model": "x-ai/grok-4.6",
        "name": "Grok 4.6",
        "score": 0.5,
        "status": "partial",
        "answer": "33923-S before 3-1-66; 34392-S from 3-1-66",
        "note": "Gave the two nut numbers in the correct before/after order, but omitted the bolt change. Earned half credit."
      },
      {
        "model": "qwen/qwen3.8-max-0902",
        "name": "Qwen 3.8 Max 0902",
        "score": 0.0,
        "status": "incomplete",
        "answer": null,
        "note": "The provider returned an error with no final answer. Scored zero; this does not establish what the model would have answered."
      },
      {
        "model": "z-ai/glm-5.3-flash",
        "name": "GLM 5.3 Flash",
        "score": 0.5,
        "status": "partial",
        "answer": "The diagram shows a dated supersession in the hardware attaching part 18A017: fastener 33923-S (bin M-32) was used 'BEFORE 3-1-66', and 'FROM 3-1-66' it was replaced by fastener 34392-S (bin M-93). In other words, the attachment hardware for 18A017 changed effective March 1, 1966, from 33923-S to 34392-S.",
        "note": "Identified the change from 33923-S to 34392-S, but omitted the bolt change. Earned half credit."
      },
      {
        "model": "qwen/qwen3.8-flash",
        "name": "Qwen 3.8 Flash",
        "score": 0.0,
        "status": "incorrect",
        "answer": "The diagram shows a dated change to one of the bolts used to attach part 18A017: the bolt 33923-S (marked \"BEFORE 3-1-66\") was replaced by 34392-S (marked \"FROM 3-1-66\"). The other attachment hardware for 18A017 (34420-S bolt, 18041 washer, and 1-500939 nut) is listed without any date change.",
        "note": "Read the nut numbers but called them bolts, and missed the actual bolt replacement. The saved rubric awarded neither criterion."
      },
      {
        "model": "bytedance-seed/seed-2-1-turbo",
        "name": "Seed 2.1 Turbo",
        "score": 0.0,
        "status": "incorrect",
        "answer": "The attachment bolt (basic number 3B236) for part 18A017 was changed effective March 1, 1966: before 3-1-66 the hardware was part number 33923-S (M-32), and from 3-1-66 onward it was replaced by part number 34392-S (M-93).",
        "note": "Read the nut numbers but described them as an attachment bolt, and omitted the actual bolt replacement. The saved rubric awarded neither criterion."
      },
      {
        "model": "deepseek/deepseek-v4-flash-vision-exp",
        "name": "DeepSeek V4 Vision Exp",
        "score": 0.0,
        "status": "incorrect",
        "answer": "The attachment hardware was changed from 35547-S to 37940-S on 3-1-66.",
        "note": "Gave 35547-S and 37940-S rather than the complete bolt numbers 355471-S and 378940-S, and omitted the nut change."
      }
    ],
    "assembly": [
      {
        "model": "openai/gpt-6-astra",
        "name": "GPT-6 Astra",
        "score": 1.0,
        "status": "correct",
        "answer": [
          {
            "instance": 1,
            "part_number": "378866-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5482",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5490",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "3397",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5A491",
            "pass": 1
          },
          {
            "instance": 4,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 4,
            "part_number": "371169-S",
            "pass": 1
          }
        ],
        "note": "Listed all 13 parts in order, including the separate copies of the washers and bushings."
      },
      {
        "model": "anthropic/claude-fable-5.1",
        "name": "Claude Fable 5.1",
        "score": 0.0,
        "status": "incorrect",
        "answer": [
          {
            "instance": 1,
            "part_number": "3368",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5A491",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "34447-S",
            "pass": 1
          }
        ],
        "note": "Listed only five parts. Omitted most of the stack, including 378866-S, 5482 and 3397, and added 3368 and 34447-S."
      },
      {
        "model": "openai/gpt-5.6-sol-pro",
        "name": "GPT-5.6 Sol Pro",
        "score": 0.0,
        "status": "incorrect",
        "answer": [
          {
            "instance": 1,
            "part_number": "378866-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5482",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5490",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "3078",
            "pass": 1
          },
          {
            "instance": 4,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 4,
            "part_number": "371169-S",
            "pass": 1
          }
        ],
        "note": "Got the first nine part numbers in order, then gave 3078 instead of 3397 (lower control arm) and omitted 5A491."
      },
      {
        "model": "google/gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "score": 0.0,
        "status": "incorrect",
        "answer": [
          {
            "instance": 1,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5490",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5482",
            "pass": 1
          },
          {
            "instance": 4,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 4,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "34447-S",
            "pass": 1
          }
        ],
        "note": "Listed 11 parts in the wrong order. Omitted 378866-S, 3397 and 5A491, and added 34447-S."
      },
      {
        "model": "x-ai/grok-4.6",
        "name": "Grok 4.6",
        "score": 0.0,
        "status": "incorrect",
        "answer": [
          {
            "instance": 1,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "55490",
            "pass": 1
          }
        ],
        "note": "Listed only four pieces: two bushings, the spacer and one washer. Omitted the rest of the 13-part stack."
      },
      {
        "model": "qwen/qwen3.8-max-0902",
        "name": "Qwen 3.8 Max 0902",
        "score": 0.0,
        "status": "incorrect",
        "answer": [
          {
            "instance": 1,
            "part_number": "3368",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5A491",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "55490",
            "pass": 1
          },
          {
            "instance": 2,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5490",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "371169-S",
            "pass": 1
          },
          {
            "instance": 3,
            "part_number": "55490",
            "pass": 1
          }
        ],
        "note": "Listed nine parts. Omitted the top nut, stabilizer bar and lower control arm, included 3368, and put 5A491 near the beginning instead of below the arm."
      },
      {
        "model": "z-ai/glm-5.3-flash",
        "name": "GLM 5.3 Flash",
        "score": 0.0,
        "status": "incomplete",
        "answer": null,
        "note": "Reached the 32,768-token output limit without a complete final answer. Scored zero; there is no completed answer to compare."
      },
      {
        "model": "qwen/qwen3.8-flash",
        "name": "Qwen 3.8 Flash",
        "score": 0.0,
        "status": "incomplete",
        "answer": null,
        "note": "The provider returned an error with no final answer. Scored zero; this does not establish what the model would have answered."
      },
      {
        "model": "bytedance-seed/seed-2-1-turbo",
        "name": "Seed 2.1 Turbo",
        "score": 0.0,
        "status": "incomplete",
        "answer": null,
        "note": "Reached the 32,768-token output limit without a complete final answer. Scored zero; there is no completed answer to compare."
      },
      {
        "model": "deepseek/deepseek-v4-flash-vision-exp",
        "name": "DeepSeek V4 Vision Exp",
        "score": 0.0,
        "status": "incorrect",
        "answer": [
          {
            "instance": 1,
            "part_number": "3A047",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5490",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "5489",
            "pass": 1
          },
          {
            "instance": 1,
            "part_number": "37169-S",
            "pass": 1
          }
        ],
        "note": "Listed four parts instead of 13. Only 5490 matches a part number in the expected stack; 37169-S is not the required 371169-S."
      }
    ]
  }
};
