import Foundation

/// A deliberately narrow story-state projection for a playtest note.
///
/// A future on-device transport may provide this without exposing its save,
/// credentials, or other engine internals. Values that look like credentials
/// are dropped before they cross the seam.
struct PlaytestStorySnapshot: Codable, Equatable {
    let act: String?
    let location: String?
    let worldLayer: String?
    let markers: [String]

    init(
        act: String? = nil,
        location: String? = nil,
        worldLayer: String? = nil,
        markers: [String] = []
    ) {
        self.act = Self.safeValue(act)
        self.location = Self.safeValue(location)
        self.worldLayer = Self.safeValue(worldLayer)
        self.markers = Array(Set(markers.compactMap(Self.safeValue))).sorted()
    }

    private enum CodingKeys: String, CodingKey {
        case act
        case location
        case worldLayer
        case markers
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.init(
            act: try container.decodeIfPresent(String.self, forKey: .act),
            location: try container.decodeIfPresent(String.self, forKey: .location),
            worldLayer: try container.decodeIfPresent(String.self, forKey: .worldLayer),
            markers: try container.decodeIfPresent([String].self, forKey: .markers) ?? []
        )
    }

    private static func safeValue(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed.count <= 80 else { return nil }

        let lowercased = trimmed.lowercased()
        let forbidden = [
            "api_key", "apikey", "client_id", "clientid", "resume_handle",
            "authorization", "bearer ",
        ]
        guard !forbidden.contains(where: lowercased.contains) else { return nil }
        let normalisedIdentifier = String(
            lowercased.filter { $0.isLetter || $0.isNumber }
        )
        let forbiddenIdentifiers = [
            "apikey", "clientid", "resumehandle", "authorization",
            "accesstoken", "sessiontoken", "authtoken", "refreshtoken",
            "clientsecret", "privatekey", "password", "credential",
        ]
        guard !forbiddenIdentifiers.contains(where: normalisedIdentifier.contains) else {
            return nil
        }
        let credentialLabelPattern = #"\b(?:access|session|auth|refresh|identity|client)?[-_\s]*(?:token|secret|password|credential|private[-_\s]*key)\s*[:=]"#
        guard lowercased.range(
            of: credentialLabelPattern,
            options: .regularExpression
        ) == nil else { return nil }
        let bearerPattern = #"\bbearer(?:[-_\s:=]|$)"#
        guard lowercased.range(of: bearerPattern, options: .regularExpression) == nil else {
            return nil
        }
        let apiKeyPattern = #"(^|[\s=])sk-[a-z0-9_-]{8,}"#
        guard lowercased.range(of: apiKeyPattern, options: .regularExpression) == nil else {
            return nil
        }

        // Client identities and tokens are long, opaque runs. Story identifiers
        // are short and legible; rejecting the ambiguous case is safer than
        // carrying a credential into a shareable file.
        let opaqueCharacters = CharacterSet.alphanumerics.union(
            CharacterSet(charactersIn: "-_=./+")
        )
        let looksOpaque = trimmed.count >= 32
            && trimmed.unicodeScalars.allSatisfy(opaqueCharacters.contains)
        return looksOpaque ? nil : trimmed
    }
}

/// One recent line, stripped of its UI identity but retaining its source.
struct PlaytestTranscriptLine: Codable, Equatable {
    let kind: TranscriptBlock.Kind
    let text: String
}

/// Run context frozen when the notebook opens, not when Save is tapped.
struct PlaytestNoteContext: Codable, Equatable {
    let capturedAt: Date
    let successfulTurnIndex: Int
    let recentTranscript: [PlaytestTranscriptLine]
    let status: Status?
    let story: PlaytestStorySnapshot?
}

/// The in-memory page shown in the sheet.
struct PlaytestNoteDraft: Equatable, Identifiable {
    let id: UUID
    let context: PlaytestNoteContext
    var body: String
}

/// A durable page in the local playtest notebook.
struct PlaytestNote: Codable, Equatable, Identifiable {
    let id: UUID
    let context: PlaytestNoteContext
    let body: String
}
